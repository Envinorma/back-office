import dash_html_components as html
from dash import Dash
from dash.development.base_component import Component

from back_office.routing import Page


def _layout(am_id: str) -> Component:
    return html.H3(f'AM {am_id}')


def _callbacks(app: Dash) -> None:
    ...


PAGE = Page(_layout, _callbacks)
