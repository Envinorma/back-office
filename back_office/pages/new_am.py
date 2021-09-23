from typing import Optional

from dash import Dash, dcc, html
from dash.development.base_component import Component

from back_office.components.edit_metadata.edit_metadata import edit_metadata
from back_office.routing import Endpoint, Page


def _page(am_id: Optional[str] = None) -> Component:
    return html.Div(
        [
            dcc.Link('< Retour à la liste des AM', href=f'/{Endpoint.INDEX}', className='btn btn-link'),
            edit_metadata(True, am_id),
        ],
        className='container mt-3',
    )


def _add_callbacks(app: Dash) -> None:
    pass


PAGE = Page(_page, _add_callbacks, True)
