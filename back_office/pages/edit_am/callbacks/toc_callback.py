from typing import List, Optional, Tuple

from bs4 import BeautifulSoup
from dash import ClientsideFunction, Dash, Input, Output, State, callback, html
from dash.development.base_component import Component
from envinorma.io.parse_html import extract_text_elements
from envinorma.models.text_elements import Title

from back_office.helpers.texts import get_truncated_str

from .. import ids
from .save_callback import count_prefix_hashtags


def _extract_lines_with_potential_id(html: BeautifulSoup) -> List[Tuple[str, Optional[str]]]:
    text_elements = extract_text_elements(html)
    strs: List[Tuple[str, Optional[str]]] = []
    for element in text_elements:
        if isinstance(element, Title):
            strs.append((element.text, element.id))
        elif isinstance(element, str):
            strs.append((element, None))
    return strs


def _make_title(line: str, id_: Optional[str]) -> Title:
    nb_hashtags = count_prefix_hashtags(line)
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


def add_callbacks(app: Dash) -> None:
    @callback(Output(ids.TOC_COMPONENT, 'children'), [Input(ids.TEXT_AREA_COMPONENT, 'value')])
    def _(text_area_content):
        if text_area_content is not None:
            return _parse_html_area_and_display_toc(text_area_content)

    app.clientside_callback(
        ClientsideFunction(namespace='clientside', function_name='get_edited_content'),
        Output(ids.TEXT_AREA_COMPONENT, 'value'),
        [Input(ids.HIDDEN_BUTTON, 'n_clicks')],
        [State(ids.TEXT_AREA_COMPONENT, 'id')],
    )
