from typing import List

from envinorma.models import ArreteMinisteriel, StructuredText
from text_diff import TextDifferences, text_differences


def _extract_lines(am: ArreteMinisteriel) -> List[str]:
    return [line for section in am.sections for line in section.text_lines(1)]


def compute_am_diff(am_before: ArreteMinisteriel, am_after: ArreteMinisteriel) -> TextDifferences:
    lines_before = _extract_lines(am_before)
    lines_after = _extract_lines(am_after)
    return text_differences(lines_before, lines_after)


def compute_text_diff(text_before: StructuredText, text_after: StructuredText) -> TextDifferences:
    lines_before = text_before.text_lines()
    lines_after = text_after.text_lines()
    return text_differences(lines_before, lines_after)
