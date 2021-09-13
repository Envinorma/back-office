from typing import List, Optional, Tuple

import dash_html_components as html
from bs4 import BeautifulSoup
from dash.dash import Dash
from dash.dependencies import Input, Output
from dash.development.base_component import Component
from envinorma.io.parse_html import extract_text_elements
from envinorma.models.text_elements import Title
from envinorma.structure import structured_text_to_text_elements

from back_office.helpers.texts import get_truncated_str
from back_office.utils import DATA_FETCHER

from .. import ids


def _extract_lines_with_potential_id(html: BeautifulSoup) -> List[Tuple[str, Optional[str]]]:
    text_elements = extract_text_elements(html)
    strs: List[Tuple[str, Optional[str]]] = []
    for element in text_elements:
        if isinstance(element, Title):
            strs.append((element.text, element.id))
        elif isinstance(element, str):
            strs.append((element, None))
    return strs


def _count_prefix_hashtags(line: str) -> int:
    for i, char in enumerate(line):
        if char != '#':
            return i
    return len(line)


def _make_title(line: str, id_: Optional[str]) -> Title:
    nb_hashtags = _count_prefix_hashtags(line)
    trunc_title = line[nb_hashtags:].strip()
    return Title(trunc_title, level=nb_hashtags, id=id_)


def _format_toc_line(title: Title) -> Component:
    trunc_title = get_truncated_str(title.text)
    trunc_title_component = html.Span(trunc_title) if title.level > 1 else html.B(trunc_title)
    return html.A(
        [html.Span(title.level * '•' + ' ', style={'color': 'grey'}), trunc_title_component], href=f'#{title.id}'
    )


def _toc(titles: List[Title]) -> Component:
    formatted_lines = [_format_toc_line(title) for title in titles]
    new_title_levels = html.P(formatted_lines)
    return html.P(new_title_levels)


def _parse_html_area_and_display_toc(html_str: str) -> Component:
    lines_and_ids = _extract_lines_with_potential_id(BeautifulSoup(html_str, 'html.parser'))
    titles = [_make_title(line, id_) for line, id_ in lines_and_ids if line.startswith('#')]
    return _toc(titles)


def _toc_from_am(am_id: str) -> Component:
    am = DATA_FETCHER.load_most_advanced_am(am_id)
    if not am:
        return html.Div(am)
    elements = structured_text_to_text_elements(am.to_text(), 0)
    return _toc([element for element in elements if isinstance(element, Title)][1:])


def add_callbacks(app: Dash) -> None:
    @app.callback(
        Output(ids.TOC_COMPONENT, 'children'), [Input(ids.TEXT_AREA_COMPONENT, 'value'), Input(ids.AM_ID, 'data')]
    )
    def _(text_area_content, am_id):
        if text_area_content is not None:
            return _parse_html_area_and_display_toc(text_area_content)
        return _toc_from_am(am_id)
