import json
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Any, DefaultDict, Dict, List, Optional, Set

import requests
from bs4 import BeautifulSoup, Tag
from envinorma.io.parse_html import extract_text_elements
from envinorma.models import StructuredText
from envinorma.structure import build_structured_text
from tqdm import tqdm

from back_office.config import AIDA_URL

_NOR_REGEXP = r'[A-Z]{4}[0-9]{7}[A-Z]'


@dataclass
class Hyperlink:
    content: str
    href: str


@dataclass
class Anchor:
    name: str
    anchored_text: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AidaData:
    page_id_to_links: Dict[str, List[Hyperlink]]
    page_id_to_anchors: Dict[str, List[Anchor]]


def _extract_nor_from_text(text: str) -> str:
    match = re.search(_NOR_REGEXP, text)
    if not match:
        raise ValueError(f'NOR not found in {text}.')
    return text[match.start() : match.end()]


def extract_nor_from_html(html: str) -> str:
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup.find_all('h5'):
        if 'NOR' in tag.text:  # type: ignore
            return _extract_nor_from_text(tag.text)  # type: ignore
    raise ValueError('NOR not found!')


def download_html(document_id: str) -> str:
    response = requests.get(AIDA_URL + document_id)
    if response.status_code != 200:
        raise ValueError(f'Request failed with status code {response.status_code}')
    return response.content.decode()


def scrap_nor(document_id: str) -> str:
    return extract_nor_from_html(download_html(document_id))


def extract_page_title(html: str) -> str:
    soup = BeautifulSoup(html, 'html.parser')
    return soup.find('h1').text  # type: ignore


def scrap_title(document_id: str) -> str:
    return extract_page_title(download_html(document_id))


def get_aida_content_area(soup: BeautifulSoup) -> Tag:
    content_area = soup.find('div', {'id': 'content-area'})
    if not content_area:
        raise ValueError('Content area not found in this AIDA page!')
    return content_area  # type: ignore


def extract_hyperlinks(html: str) -> List[Hyperlink]:
    soup = BeautifulSoup(html, 'html.parser')
    return [
        Hyperlink(tag.text, tag['href'])  # type: ignore
        for tag in get_aida_content_area(soup).find_all('a')
        if 'href' in tag.attrs  # type: ignore
    ]


_AIDA_PREFIXES_TO_REMOVE = [
    'http://gesreg03-bo.gesreg.fr/gesdoc_application/1/section/edit/',
    'http://gesreg03-bo.gesreg.fr/gesdoc_application/1/section/add/35358/',
    'http://',
]


def _starts_with_hash(str_: str) -> bool:
    return bool(str_ and str_[0] == '#')


def _cleanup_aida_href(str_: str, document_id: str) -> str:
    tmp_str = str_
    for prefix in _AIDA_PREFIXES_TO_REMOVE:
        tmp_str = tmp_str.replace(prefix, '')
    url = AIDA_URL + '{}'
    return url.format(f'{document_id}{tmp_str}' if _starts_with_hash(tmp_str) else tmp_str)


def _cleanup_aida_link(link: Hyperlink, document_id: str) -> Hyperlink:
    return Hyperlink(href=_cleanup_aida_href(link.href, document_id), content=link.content)


def keep_solid_aida_links(hyperlinks: List[Hyperlink]) -> List[Hyperlink]:
    content_to_targets: DefaultDict[str, List[str]] = defaultdict(list)
    for link in hyperlinks:
        content_to_targets[link.content].append(link.href)
    valid_contents = {
        content for content, targets in content_to_targets.items() if len(set(targets)) <= 1 and len(content) >= 4
    }
    return [link for link in hyperlinks if link.content in valid_contents]


def extract_all_urls_from_content_page(document_id: str) -> List[Hyperlink]:
    html = download_html(document_id)
    raw_links = extract_hyperlinks(html)
    return keep_solid_aida_links([_cleanup_aida_link(link, document_id) for link in raw_links])


def extract_anchor_if_present_in_tag(tag: Tag) -> Optional[Anchor]:
    a_tag = tag.find('a')
    if not a_tag:
        return None
    name = a_tag.attrs.get('name')  # type: ignore
    if not name:
        return None
    anchored_text = tag.text.strip()
    return Anchor(name, anchored_text)


def extract_anchors_from_soup(content_area: Tag) -> List[Anchor]:
    candidates = [
        extract_anchor_if_present_in_tag(tag)  # type: ignore
        for title_level in [f'h{i}' for i in range(1, 7)]
        for tag in content_area.find_all(title_level)
    ]

    return [anchor for anchor in candidates if anchor]


def extract_anchors(html: str) -> List[Anchor]:
    soup = BeautifulSoup(html, 'html.parser')
    content_area = get_aida_content_area(soup)
    return extract_anchors_from_soup(content_area)


def _keep_non_ambiguous_anchors(anchors: List[Anchor]) -> List[Anchor]:
    text_to_anchors: DefaultDict[str, Set[str]] = defaultdict(set)
    for anchor in anchors:
        text_to_anchors[anchor.anchored_text].add(anchor.name)
    return [
        Anchor(list(names)[0], anchored_text) for anchored_text, names in text_to_anchors.items() if len(names) == 1
    ]


def extract_all_anchors_from_aida(document_id: str) -> List[Anchor]:
    html = download_html(document_id)
    raw_anchors = extract_anchors(html)
    return _keep_non_ambiguous_anchors(raw_anchors)


def scrap_all_anchors() -> None:
    arretes_ministeriels = json.load(open('data/arretes_ministeriels.json'))
    page_ids = [am['aida_page'] for am in arretes_ministeriels]
    page_id_to_anchors_json: Dict[str, List[Dict[str, Any]]] = {}
    for page_id in tqdm(page_ids):
        try:
            page_id_to_anchors_json[page_id] = [anchor.to_dict() for anchor in extract_all_anchors_from_aida(page_id)]
        except Exception as exc:  # pylint: disable=broad-except
            print(exc)
    json.dump(page_id_to_anchors_json, open('data/aida/hyperlinks/page_id_to_anchors.json', 'w'), ensure_ascii=False)


def parse_aida_text(document_id: str) -> Optional[StructuredText]:
    page_content = download_html(document_id)
    soup = BeautifulSoup(page_content, 'html.parser')
    content_div = soup.find('div', {'id': 'content-inner'})
    if not content_div:
        return None
    elements = extract_text_elements(content_div)
    return build_structured_text('', elements)
