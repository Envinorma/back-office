from typing import Optional

import dash_bootstrap_components as dbc
from dash import Dash, dcc, html
from dash.development.base_component import Component
from envinorma.models import ArreteMinisteriel, StructuredText

from back_office.components.am_side_nav import page_with_sidebar
from back_office.routing import Endpoint, Page
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


def _edit_button(am_id: str) -> Component:
    return dcc.Link('Éditer les thèmes', className='btn btn-primary', href=f'/{Endpoint.EDIT_TOPICS}/{am_id}')


def _edit(am_id: str) -> Component:
    return html.Div([_edit_button(am_id)], style={'text-align': 'right'})


def _left_col() -> Component:
    address = html.Span('drieat-if.envinorma@developpement-durable.gouv.fr', style={'font-size': '0.8em'})
    alert = dbc.Alert(
        ['Pour toute suggestion de modification, veuillez en faire part par email à l\'adresse ', address],
        color='primary',
        className='mt-3',
    )
    return html.Div([html.H3('Thèmes'), alert])


def _layout(am_id: str) -> Component:
    row = html.Div(
        [
            html.Div(_left_col(), className='col-3'),
            html.Div(className='col-9', children=_am_topics(DATA_FETCHER.load_am(am_id))),
        ],
        className='row',
    )
    return html.Div([_edit(am_id), html.Hr(), row])


def _callbacks(app: Dash) -> None:
    ...


def _page(am_id: str) -> Component:
    return page_with_sidebar(_layout(am_id), am_id)


PAGE = Page(_page, _callbacks, False)
