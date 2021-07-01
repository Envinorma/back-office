from typing import Optional

import dash_html_components as html
from dash import Dash
from dash.development.base_component import Component
from envinorma.models import AMMetadata, ArreteMinisteriel, StructuredText

from back_office.utils import DATA_FETCHER


def _topic_name(section: StructuredText) -> Optional[str]:
    topic = section.annotations.topic if section.annotations else None
    return topic.name if topic else None


def _title(section: StructuredText) -> Component:
    topic_name = _topic_name(section)
    badge = html.Span(topic_name, className='badge badge-primary') if topic_name else ''
    return html.Span([f'{section.title.text} ', badge], style={'font-size': '0.8em'})


def _section_topics(section: StructuredText) -> Component:
    style = {'margin-top': '3px', 'background-color': '#007bff33'} if _topic_name(section) else {}
    return html.Div(
        [_title(section), *[_section_topics(sub) for sub in section.sections]],
        style={'border-left': '3px solid #007bff', 'padding-left': '10px', **style},
    )


def _am_topics(am: Optional[ArreteMinisteriel]) -> Component:
    if not am:
        return html.Div('AM non initialisé')
    return html.Div([_section_topics(section) for section in am.sections])


def _layout(am: AMMetadata) -> Component:
    return html.Div(
        [
            html.H4('Thèmes', className='row, mb-3'),
            html.Div(className='row', children=_am_topics(DATA_FETCHER.load_most_advanced_am(am.cid))),
        ]
    )


def _callbacks(app: Dash) -> None:
    ...


TAB = ('Thèmes', _layout, _callbacks)
