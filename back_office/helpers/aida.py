import re
from copy import copy
from dataclasses import replace
from typing import List, Optional

import requests
from bs4 import BeautifulSoup
from bs4.element import Comment, NavigableString, Tag
from envinorma.io.parse_html import extract_text_elements
from envinorma.models import StructuredText
from envinorma.models.arrete_ministeriel import ArreteMinisteriel
from envinorma.models.text_elements import EnrichedString
from envinorma.structure import build_structured_text

from back_office.config import AIDA_URL

NOR_REGEXP = r'[A-Z]{4}[0-9]{7}[A-Z]'


def _download_html(document_id: str) -> str:
    response = requests.get(AIDA_URL + document_id)
    if response.status_code != 200:
        raise ValueError(f'Request failed with status code {response.status_code}')
    return response.content.decode()


def _remove_comments(soup: Tag) -> Tag:
    comments = soup.findAll(text=lambda text: isinstance(text, Comment))
    for comment in comments:
        comment.extract()
    return soup


def _parse_aida_text(document_id: str) -> Optional[StructuredText]:
    page_content = _download_html(document_id)
    soup = BeautifulSoup(page_content, 'html.parser')
    content_div = soup.find('div', {'id': 'content-inner'})
    if not content_div or isinstance(content_div, NavigableString):
        return None
    clean_tree = _remove_comments(content_div)
    elements = extract_text_elements(clean_tree)
    return build_structured_text('', elements)


def _extract_section(text: StructuredText) -> StructuredText:
    if len(text.sections) == 1:
        return text.sections[0]
    raise NotImplementedError(
        f'Cannot handle more than one section when extracting text from AIDA. Got {len(text.sections)}'
    )


def _remove_sections_before_visa(sections: List[StructuredText]) -> List[StructuredText]:
    visa_section = None
    index = 0
    for section_index, section in enumerate(sections):
        if section.title.text.lower().startswith('vus'):
            visa_section = section
            index = section_index
            break
    if visa_section:
        return sections[index + 1 :]
    return sections


_LONG_TITLE_REGEXP = re.compile(r"Article (.*) de l(.*)arrêté du (.*)")


def _truncate_title(title: str) -> str:
    if re.match(_LONG_TITLE_REGEXP, title):
        return title.split("de l")[0].strip()
    return title


def _truncate_unneccessarily_long_titles(text: StructuredText) -> StructuredText:
    new_text = copy(text)
    new_text.sections = [_truncate_unneccessarily_long_titles(section) for section in new_text.sections]
    new_text.title.text = _truncate_title(new_text.title.text)
    return new_text


def _remove_empty_alineas(text: StructuredText) -> StructuredText:
    new_text = copy(text)
    new_text.sections = [_remove_empty_alineas(section) for section in new_text.sections]
    new_text.outer_alineas = [
        replace(alinea, text=alinea.text.strip())
        for alinea in text.outer_alineas
        if (alinea.text.strip() or alinea.table)
    ]
    return new_text


def _clean_section(text: StructuredText) -> StructuredText:
    new_text = copy(text)
    new_text.sections = _remove_sections_before_visa(text.sections)
    return _remove_empty_alineas(_truncate_unneccessarily_long_titles(new_text))


def extract_aida_am(page_id: str, am_id: str) -> Optional[ArreteMinisteriel]:
    text = _parse_aida_text(page_id)
    if not text:
        return None
    main_section = _extract_section(text)
    clean_section = _clean_section(main_section)
    return _build_am(clean_section, am_id)


def _build_am(section: StructuredText, am_id: str) -> ArreteMinisteriel:
    if section.outer_alineas:
        new_sections = [StructuredText(EnrichedString(''), section.outer_alineas, [], None)] + section.sections
    else:
        new_sections = section.sections
    return ArreteMinisteriel(title=section.title, sections=new_sections, visa=[], id=am_id)
