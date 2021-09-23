import dash_bootstrap_components as dbc
from dash import Dash, dcc, html
from dash.development.base_component import Component

from back_office.components.am_component import am_with_summary_component
from back_office.components.am_side_nav import page_with_sidebar
from back_office.routing import Endpoint, Page
from back_office.utils import DATA_FETCHER


def _link(text: str, href: str) -> Component:
    return dcc.Link(text, className='btn btn-link', href=href)


def _buttons(am_id: str) -> Component:
    href = f'/{Endpoint.EDIT_AM}/{am_id}'
    return html.Div(
        [
            _link('Comparer avec la version Légifrance', f'/am_compare/{am_id}/legifrance'),
            _link('Comparer avec la version AIDA', f'/am_compare/{am_id}/aida'),
            _link('Comparer deux versions légifrance successives', f'/compare/id/{am_id}'),
            dbc.Button('Éditer le contenu', color='primary float-end', href=href),
        ]
    )


def _am(am_id: str) -> Component:
    am = DATA_FETCHER.load_am(am_id)
    if not am or not am.sections:
        return html.P('AM non initialisé.')
    return am_with_summary_component(am, first_level=3, with_topics=False)


def _component(am_id: str) -> Component:
    am = DATA_FETCHER.load_am_metadata(am_id)
    if not am:
        return html.P('AM introuvable')
    return html.Div([_buttons(am_id), html.Hr(), _am(am_id)])


def _page(am_id: str) -> Component:
    return page_with_sidebar(_component(am_id), am_id)


def _callbacks(app: Dash) -> None:
    ...


PAGE = Page(_page, _callbacks, False)
