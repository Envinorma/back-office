from copy import copy
from typing import List

from envinorma.models import ArreteMinisteriel, EnrichedString, StructuredText

from back_office.utils import DATA_FETCHER


class SaveError(Exception):
    pass


def _load_am(am_id: str) -> ArreteMinisteriel:
    am = DATA_FETCHER.load_am(am_id)
    if not am:
        raise SaveError('AM introuvable, modifications non effectuées.')
    return am


def _update_alineas_in_section(
    section: StructuredText, section_id: str, new_alineas: List[EnrichedString]
) -> StructuredText:
    new_section = copy(section)
    if section.id == section_id:
        new_section.outer_alineas = new_alineas
    else:
        new_section.sections = [_update_alineas_in_section(sub, section_id, new_alineas) for sub in section.sections]
    return new_section


def _update_alineas(am: ArreteMinisteriel, section_id: str, alineas: List[EnrichedString]) -> ArreteMinisteriel:
    new_am = copy(am)
    new_am.sections = [_update_alineas_in_section(section, section_id, alineas) for section in am.sections]
    return new_am


def edit_am_alineas(am_id: str, section_id: str, new_alineas: List[EnrichedString]) -> None:
    new_am = _update_alineas(_load_am(am_id), section_id, new_alineas)
    DATA_FETCHER.upsert_am(am_id, new_am)


def _update_title_in_section(section: StructuredText, section_id: str, new_title: str) -> StructuredText:
    new_section = copy(section)
    if section.id == section_id:
        new_section.title.text = new_title
    else:
        new_section.sections = [_update_title_in_section(sub, section_id, new_title) for sub in section.sections]
    return new_section


def _update_title(am: ArreteMinisteriel, section_id: str, new_title: str) -> ArreteMinisteriel:
    new_am = copy(am)
    new_am.sections = [_update_title_in_section(section, section_id, new_title) for section in am.sections]
    return new_am


def edit_am_title(am_id: str, section_id: str, new_title: str) -> None:
    new_am = _update_title(_load_am(am_id), section_id, new_title)
    DATA_FETCHER.upsert_am(am_id, new_am)


def _delete_section_recurse(section: StructuredText, section_id: str) -> StructuredText:
    new_section = copy(section)
    new_section.sections = [
        _delete_section_recurse(sub, section_id) for sub in section.sections if sub.id != section_id
    ]
    return new_section


def _delete_section(am: ArreteMinisteriel, section_id: str) -> ArreteMinisteriel:
    new_am = copy(am)
    new_am.sections = [
        _delete_section_recurse(section, section_id) for section in am.sections if section.id != section_id
    ]
    return new_am


def delete_am_section(am_id: str, section_id: str) -> None:
    new_am = _delete_section(_load_am(am_id), section_id)
    DATA_FETCHER.upsert_am(am_id, new_am)


def _insert_empty_section_recurse(section: StructuredText, section_id: str) -> StructuredText:
    new_section = copy(section)
    new_section.sections = [_insert_empty_section_recurse(sub, section_id) for sub in section.sections]
    if section.id == section_id:
        new_section.sections.append(StructuredText(EnrichedString(''), [], [], None))
    return new_section


def _insert_empty_section(am: ArreteMinisteriel, section_id: str) -> ArreteMinisteriel:
    new_am = copy(am)
    new_am.sections = [_insert_empty_section_recurse(section, section_id) for section in am.sections]
    return new_am


def insert_empty_section(am_id: str, section_id: str) -> None:
    new_am = _insert_empty_section(_load_am(am_id), section_id)
    DATA_FETCHER.upsert_am(am_id, new_am)
