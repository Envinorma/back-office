from dash import Dash, dcc
from dash.development.base_component import Component

from back_office.routing import Endpoint, Page


def _page(am_id: str) -> Component:
    return dcc.Location(id='redirect-to-apercu', href=f'/{Endpoint.AM}/{am_id}/{Endpoint.AM_APERCU}')


def _add_callbacks(app: Dash) -> None:
    pass


PAGE = Page(_page, _add_callbacks, True)
