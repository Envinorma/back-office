import json
import traceback
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, TypeVar, Union

from envinorma.data_fetcher import DataFetcher

from back_office.config import PSQL_DSN

DATA_FETCHER = DataFetcher(PSQL_DSN)


@lru_cache
def _load_am_id_occurences() -> Dict[str, int]:
    filename = Path(__file__).parent.parent / 'data' / 'am_id_to_nb_classements.json'
    assert filename.exists()
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


T = TypeVar('T')


def ensure_not_none(option: Optional[T]) -> T:
    if option is None:
        raise ValueError('Expecting non None object.')
    return option


class RouteParsingError(Exception):
    pass


def generate_id(filename: str, suffix: str) -> str:
    prefix = Path(filename).name.replace('.py', '').replace('_', '-').replace('.', '-')
    return prefix + '-' + suffix


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
    ADD_CONDITION = 'add_condition'
    ADD_ALTERNATIVE_SECTION = 'add_alternative_section'
    ADD_WARNING = 'ADD_WARNING'
