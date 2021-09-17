import string
from typing import List

from envinorma.models import ArreteMinisteriel, StructuredText
from text_diff import TextDifferences, text_differences
from unidecode import unidecode

_SIMPLE_CHARS = set(string.ascii_letters + string.digits + string.whitespace)


def _clean_line(line: str) -> str:
    res = str(unidecode(line)).strip()
    return ''.join(c for c in res if c in _SIMPLE_CHARS)


def extract_am_lines(am: ArreteMinisteriel, normalize_text: bool) -> List[str]:
    lines = [line for section in am.sections for line in section.text_lines(1)]
    if normalize_text:
        return [_clean_line(line) for line in lines]
    return lines


def compute_am_diff(am_before: ArreteMinisteriel, am_after: ArreteMinisteriel, normalize_text: bool) -> TextDifferences:
    lines_before = extract_am_lines(am_before, normalize_text)
    lines_after = extract_am_lines(am_after, normalize_text)
    return text_differences(lines_before, lines_after)


def compute_text_diff(text_before: StructuredText, text_after: StructuredText) -> TextDifferences:
    lines_before = text_before.text_lines()
    lines_after = text_after.text_lines()
    return text_differences(lines_before, lines_after)
