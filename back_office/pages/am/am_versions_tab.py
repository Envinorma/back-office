import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash import Dash
from dash.dependencies import Input, Output, State
from dash.development.base_component import Component
from envinorma.models import AMMetadata

from back_office.components.parametric_am_list import parametric_am_list_callbacks, parametric_am_list_component
from back_office.helpers.generate_final_am import load_am_versions

_PREFIX = 'am-versions-tab'
_LOAD_BUTTON = f'{_PREFIX}-load-button'
_AM_ID = f'{_PREFIX}-am-id'
_OUTPUT = f'{_PREFIX}-output'


def _versions(am_id: str) -> Component:
    return parametric_am_list_component(load_am_versions(am_id), _PREFIX)


def _layout(am_metadata: AMMetadata) -> Component:
    return html.Div(
        [
            html.Button('Charger les versions', id=_LOAD_BUTTON, className='btn btn-primary'),
            dcc.Store(data=am_metadata.cid, id=_AM_ID),
            dbc.Spinner(html.Div(), id=_OUTPUT),
        ]
    )


def _callbacks(app: Dash) -> None:
    parametric_am_list_callbacks(app, _PREFIX)

    @app.callback(
        Output(_OUTPUT, 'children'), Input(_LOAD_BUTTON, 'n_clicks'), State(_AM_ID, 'data'), prevent_initial_call=True
    )
    def load_versions(_, am_id: str):
        return _versions(am_id)


TAB = ('Versions Envinorma', _layout, _callbacks)
