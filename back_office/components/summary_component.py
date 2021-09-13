from typing import List, Optional

from dash import html
from dash.development.base_component import Component
from envinorma.models import StructuredText

from back_office.helpers.texts import get_truncated_str


def _topic_name(section: StructuredText) -> Optional[str]:
    topic = section.annotations.topic if section.annotations else None
    return topic.name if topic else None


def _badge(section: StructuredText) -> Component:
    topic_name = _topic_name(section)
    return html.Span(topic_name, className='badge badge-secondary') if topic_name else html.Span()


def _build_summary_line(text: StructuredText, with_dots: bool, with_topics: bool, depth: int) -> Component:
    prefix = (depth * '•' + ' ') if with_dots else ''
    trunc_title = prefix + get_truncated_str(text.title.text)
    class_name = 'level_0' if depth <= 1 else 'level_1'
    final_line = html.Span([trunc_title, _badge(text)]) if with_topics else html.Span(trunc_title)
    return html.Dd(html.A(final_line, href=f'#{text.id}', className=class_name))


def _build_summary_lines(text: StructuredText, with_dots: bool, with_topics: bool, depth: int = 0) -> List[Component]:
    lines = [
        _build_summary_line(text, with_dots, with_topics, depth),
        *[
            comp
            for section in text.sections
            for comp in _build_summary_lines(section, with_dots, with_topics, depth + 1)
        ],
    ]
    return lines


def summary_component(text: StructuredText, with_dots: bool = True, with_topics: bool = True) -> Component:
    return html.Dl(_build_summary_lines(text, with_dots, with_topics), className='summary')
