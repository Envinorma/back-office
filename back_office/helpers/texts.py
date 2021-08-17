from typing import List, Optional

from envinorma.models import ArreteMinisteriel, Ints, StructuredText


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
