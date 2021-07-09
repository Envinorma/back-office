from typing import List

from bs4 import BeautifulSoup
from envinorma.io.parse_html import extract_text_elements
from envinorma.models.text_elements import EnrichedString, Linebreak, Table, TextElement, Title


def _alinea_to_str(alinea: EnrichedString) -> str:
    if alinea.table:
        return alinea.table.to_html()
    return alinea.text


def alineas_to_textarea_value(alineas: List[EnrichedString]) -> str:
    return '\n'.join([_alinea_to_str(alinea) for alinea in alineas])


def _is_empty(element: TextElement) -> bool:
    if isinstance(element, str) and not element.strip():
        return True
    return False


def _element_to_alinea(text_element: TextElement) -> EnrichedString:
    if isinstance(text_element, Title):
        raise ValueError('Unexpected title.')
    if isinstance(text_element, Table):
        return EnrichedString('', [], text_element)
    if isinstance(text_element, Linebreak):
        raise ValueError('Unexpected linebreak.')
    return EnrichedString(text_element)


def _convert_to_alineas(text_elements: List[TextElement]) -> List[EnrichedString]:
    return [_element_to_alinea(element) for element in text_elements]


def textarea_value_to_alineas(text_area_value: str) -> List[EnrichedString]:
    soup = BeautifulSoup(text_area_value, 'html.parser')
    text_elements = extract_text_elements(soup)
    split_lines = [
        line
        for el in text_elements
        for line in (el.split('\n') if isinstance(el, str) else [el])
        if not _is_empty(line)
    ]
    return _convert_to_alineas(split_lines)
