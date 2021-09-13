from typing import List

import dash_html_components as html
from dash.development.base_component import Component
from envinorma.models import ArreteMinisteriel, StructuredText
from envinorma.models.text_elements import Table, TextElement, Title
from envinorma.structure import structured_text_to_text_elements


def _text_to_elements(text: StructuredText) -> List[TextElement]:
    return structured_text_to_text_elements(text, 0)


def _element_to_component(element: TextElement) -> Component:
    if isinstance(element, Table):
        return html.P(element.to_html())
    elif isinstance(element, Title):
        classname = f'H{element.level + 3}' if element.level <= 3 else 'H6'
        return getattr(html, classname)('#' * element.level + ' ' + element.text, id=element.id)
    elif isinstance(element, str):
        return html.P(element)
    raise NotImplementedError(f'Not implemented for type {type(element)}')


def text_area_value(am: ArreteMinisteriel) -> List[Component]:
    text_elements = _text_to_elements(am.to_text())[1:]  # Don't modify main title.
    return [_element_to_component(el) for el in text_elements]
