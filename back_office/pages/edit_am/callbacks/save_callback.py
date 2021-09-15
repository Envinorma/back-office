import traceback
from typing import List, Optional

from bs4 import BeautifulSoup
from dash import Dash, Input, Output, State, dcc, html
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
from envinorma.io.parse_html import extract_text_elements
from envinorma.models import StructuredText
from envinorma.models.lost_topic import LostTopic
from envinorma.models.text_elements import TextElement, Title
from envinorma.structure import build_structured_text

from back_office.components import alert, error_component, success_component
from back_office.routing import Endpoint
from back_office.utils import DATA_FETCHER

from .. import ids


class TextAreaHandlingError(Exception):
    pass


def count_prefix_hashtags(line: str) -> int:
    for i, char in enumerate(line):
        if char != '#':
            return i
    return len(line)


def _build_title(line: str) -> Title:
    nb_hastags = count_prefix_hashtags(line)
    return Title(line[nb_hastags:].strip(), level=nb_hastags)


def _clean_element(element: TextElement) -> TextElement:
    if not isinstance(element, (Title, str)):
        return element
    str_ = element.text if isinstance(element, Title) else element
    if not str_.startswith('#'):
        return str_
    return _build_title(str_)


def _remove_hashtags_from_elements(elements: List[TextElement]) -> List[TextElement]:
    return [_clean_element(el) for el in elements]


def _parse_table(element: TextElement) -> TextElement:
    if isinstance(element, str) and '<table>' in element:
        try:
            return extract_text_elements(BeautifulSoup(element, 'html.parser'))[0]
        except Exception:
            return element
    return element


def _parse_tables(elements: List[TextElement]) -> List[TextElement]:
    return [_parse_table(element) for element in elements]


def _build_new_elements(am_soup: BeautifulSoup) -> List[TextElement]:
    elements = _parse_tables(extract_text_elements(am_soup))

    return _remove_hashtags_from_elements(elements)


def _ensure_no_outer_alineas(new_text: StructuredText) -> None:
    if new_text.outer_alineas:
        raise TextAreaHandlingError(
            'Les premiers alinéas ne doivent pas être placés avant le titre. '
            'Enlever les alinéas ou ajouter un titre.'
        )


def _create_new_text(new_am_str: str) -> StructuredText:
    new_am_soup = BeautifulSoup(new_am_str, 'html.parser')
    new_elements = _build_new_elements(new_am_soup)
    new_text = build_structured_text('', new_elements)
    _ensure_no_outer_alineas(new_text)
    return new_text


def extract_text_from_html(new_am: str) -> List[StructuredText]:
    new_text = _create_new_text(new_am)
    return new_text.sections


def _parse_and_save_text(am_id: str, new_am_text: str) -> List[LostTopic]:
    am = DATA_FETCHER.load_most_advanced_am(am_id)
    if not am:
        raise TextAreaHandlingError(f'L\'arrete ministériel {am_id} n\'existe pas.')
    new_am, lost_topics = am.create_copy_with_new_content(extract_text_from_html(new_am_text))
    DATA_FETCHER.upsert_structured_am(am_id, new_am)
    return lost_topics


def _stringify_lost_topic(lost_topic: LostTopic) -> str:
    return '[{}], thème : {}'.format(' / '.join(lost_topic.section_titles), lost_topic.topic.value)


def _stringify_lost_topics(lost_topics: List[LostTopic]) -> str:
    return '\n'.join(map(_stringify_lost_topic, lost_topics))


def _lost_topics_message(lost_topics: List[LostTopic]) -> str:
    lost_topics_str = _stringify_lost_topics(lost_topics)
    if len(lost_topics) > 1:
        return f'Les {len(lost_topics)} thèmes suivants n\'ont pas pu être réaffectés :\n{lost_topics_str}. Pensez à les vérifier.'
    return f'Le thème suivant n\'a pas pu être réaffecté :\n{lost_topics_str}. Pensez à le réaffecter si nécessaire.'


def _extract_form_value_and_save_text(am_id: str, text_area_content: str) -> Component:
    try:
        lost_topics = _parse_and_save_text(am_id, text_area_content)
    except TextAreaHandlingError as exc:
        return error_component(f'Erreur pendant l\'enregistrement. Détails de l\'erreur:\n{str(exc)}')
    except Exception:  # pylint: disable=broad-except
        component = error_component(
            f'Erreur inattendue pendant l\'enregistrement. Détails de l\'erreur:\n{traceback.format_exc()}'
        )
        return component
    if lost_topics:
        return alert('Enregistrement réussi. ' + _lost_topics_message(lost_topics), 'warning')
    return html.Div(
        [
            success_component('Enregistrement réussi.'),
            dcc.Location(id='redirect-save-callback', pathname=f'/{Endpoint.AM}/{am_id}'),
        ]
    )


def add_callbacks(app: Dash) -> None:
    @app.callback(
        Output(ids.SAVE_OUTPUT, 'children'),
        Input(ids.SAVE_BUTTON, 'n_clicks'),
        State(ids.TEXT_AREA_COMPONENT, 'value'),
        State(ids.AM_ID, 'data'),
        prevent_initial_call=True,
    )
    def _save_callback(_, text_area_value: Optional[str], am_id: str) -> Component:
        if not text_area_value:
            raise PreventUpdate
        return _extract_form_value_and_save_text(am_id, text_area_value)
