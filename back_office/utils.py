import json
import logging
import os
import random
import traceback
from datetime import date, datetime
from enum import Enum
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple, TypeVar, Union

import requests
from envinorma.data_fetcher import DataFetcher
from envinorma.from_legifrance.legifrance_to_am import legifrance_to_arrete_ministeriel
from envinorma.models import ArreteMinisteriel, Ints, StructuredText
from leginorma import LegifranceClient, LegifranceText
from text_diff import TextDifferences, text_differences

from back_office.config import (
    LEGIFRANCE_CLIENT_ID,
    LEGIFRANCE_CLIENT_SECRET,
    PSQL_DSN,
    SLACK_ENRICHMENT_NOTIFICATION_URL,
)

LEGIFRANCE_CLIENT = None
DATA_FETCHER = DataFetcher(PSQL_DSN)


def get_legifrance_client() -> LegifranceClient:
    global LEGIFRANCE_CLIENT
    if not LEGIFRANCE_CLIENT:
        LEGIFRANCE_CLIENT = LegifranceClient(LEGIFRANCE_CLIENT_ID, LEGIFRANCE_CLIENT_SECRET)
    return LEGIFRANCE_CLIENT


@lru_cache
def _load_am_id_occurences() -> Dict[str, int]:
    relative_filename = 'data/am_id_to_nb_classements.json'
    filename = __file__.replace('back_office/utils.py', relative_filename)
    assert relative_filename in filename
    assert os.path.exists(filename)
    return json.load(open(filename))


AM_ID_TO_NB_CLASSEMENTS = _load_am_id_occurences()


def assert_int(value: Any) -> int:
    if not isinstance(value, int):
        raise ValueError(f'Expecting type int, received type {type(value)}')
    return value


def assert_str(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError(f'Expecting type str, received type {type(value)}')
    return value


def assert_list(value: Any) -> List:
    if not isinstance(value, list):
        raise ValueError(f'Expecting type list, received type {type(value)}')
    return value


def get_subsection(path: Ints, text: StructuredText) -> StructuredText:
    if not path:
        return text
    return get_subsection(path[1:], text.sections[path[0]])


def get_section(path: Ints, am: ArreteMinisteriel) -> StructuredText:
    return get_subsection(path[1:], am.sections[path[0]])


def safe_get_subsection(path: Ints, text: StructuredText) -> Optional[StructuredText]:
    if not path:
        return text
    if path[0] >= len(text.sections):
        return None
    return safe_get_subsection(path[1:], text.sections[path[0]])


def safe_get_section(path: Ints, am: ArreteMinisteriel) -> Optional[StructuredText]:
    if not path or len(path) == 0:
        return None
    if path[0] >= len(am.sections):
        return None
    return safe_get_subsection(path[1:], am.sections[path[0]])


def get_section_title(path: Ints, am: ArreteMinisteriel) -> Optional[str]:
    if not path:
        return 'Arrêté complet.'
    if path[0] >= len(am.sections):
        return None
    section = safe_get_subsection(path[1:], am.sections[path[0]])
    if not section:
        return None
    return section.title.text


def get_traversed_titles_rec(path: Ints, text: StructuredText) -> Optional[List[str]]:
    if not path:
        return [text.title.text]
    if path[0] >= len(text.sections):
        return None
    titles = get_traversed_titles_rec(path[1:], text.sections[path[0]])
    if titles is None:
        return None
    return [text.title.text] + titles


def get_traversed_titles(path: Ints, am: ArreteMinisteriel) -> Optional[List[str]]:
    if not path:
        return ['Arrêté complet.']
    if path[0] >= len(am.sections):
        return None
    return get_traversed_titles_rec(path[1:], am.sections[path[0]])


def get_truncated_str(str_: str, _max_len: int = 80) -> str:
    truncated_str = str_[:_max_len]
    if len(str_) > _max_len:
        return truncated_str[:-5] + '[...]'
    return truncated_str


def split_route(route: str) -> Tuple[str, str]:
    assert route.startswith('/')
    pieces = route[1:].split('/')
    return '/' + pieces[0], ('/' + '/'.join(pieces[1:])) if pieces[1:] else ''


class RouteParsingError(Exception):
    pass


def extract_legifrance_am(am_id: str, date_: Optional[date] = None) -> ArreteMinisteriel:
    date_ = date_ or date.today()
    datetime_ = datetime(date_.year, date_.month, date_.day)
    legifrance_current_version = LegifranceText.from_dict(get_legifrance_client().consult_law_decree(am_id, datetime_))
    random.seed(legifrance_current_version.title)
    return legifrance_to_arrete_ministeriel(legifrance_current_version, am_id=am_id)


def _extract_lines(am: ArreteMinisteriel) -> List[str]:
    return [line for section in am.sections for line in section.text_lines(1)]


def compute_am_diff(am_before: ArreteMinisteriel, am_after: ArreteMinisteriel) -> TextDifferences:
    lines_before = _extract_lines(am_before)
    lines_after = _extract_lines(am_after)
    return text_differences(lines_before, lines_after)


def compute_text_diff(text_before: StructuredText, text_after: StructuredText) -> TextDifferences:
    lines_before = text_before.text_lines()
    lines_after = text_after.text_lines()
    return text_differences(lines_before, lines_after)


def generate_id(filename: str, suffix: str) -> str:
    prefix = filename.split('/')[-1].replace('.py', '').replace('_', '-')
    return prefix + '-' + suffix


class SlackChannel(Enum):
    ENRICHMENT_NOTIFICATIONS = 'ENRICHMENT_NOTIFICATIONS'

    def slack_url(self) -> str:
        if self == self.ENRICHMENT_NOTIFICATIONS:
            return SLACK_ENRICHMENT_NOTIFICATION_URL
        raise NotImplementedError(f'Missing slack channel url {self}.')


def send_slack_notification(message: str, channel: SlackChannel) -> None:
    url = channel.slack_url()
    answer = requests.post(url, json={'text': message})
    if not (200 <= answer.status_code < 300):
        logging.error('Error with status code', answer.status_code)
        logging.error(answer.content.decode())


def write_json(obj: Union[Dict, List], filename: str, safe: bool = False, pretty: bool = True) -> None:
    indent = 4 if pretty else None
    with open(filename, 'w') as file_:
        if not safe:
            json.dump(obj, file_, indent=indent, sort_keys=True, ensure_ascii=False)
        else:
            try:
                json.dump(obj, file_, indent=indent, sort_keys=True, ensure_ascii=False)
            except Exception:  # pylint: disable=broad-except
                print(traceback.format_exc())


class AMOperation(Enum):
    INIT = 'init'
    EDIT_STRUCTURE = 'edit_structure'
    ADD_CONDITION = 'add_condition'
    ADD_ALTERNATIVE_SECTION = 'add_alternative_section'
    ADD_WARNING = 'ADD_WARNING'


T = TypeVar('T')


def ensure_not_none(option: Optional[T]) -> T:
    if option is None:
        raise ValueError('Expecting non None object.')
    return option
