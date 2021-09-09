import traceback
from typing import List
from urllib.parse import quote_plus

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash import Dash
from dash.dependencies import Input, Output
from dash.development.base_component import Component

from back_office.helpers.login import get_current_user
from back_office.helpers.upload_ams import upload_ams
from back_office.routing import Endpoint, Page
from back_office.utils import generate_id

_BUTTON = generate_id('upload-ams', 'trigger-upload')
_EXPORT_OUTPUT = generate_id('upload-ams', 'export-output')


def _layout_if_logged() -> Component:
    return html.Div(
        [
            html.H3('Exporter la base des arrêtés ministériels'),
            html.P('Cliquer sur le bouton ci-dessous pour exporter les AM dans OVH (environ 2 minutes)'),
            html.Button('Exporter', id=_BUTTON, className='btn btn-primary mb-3'),
            html.Div(dbc.Spinner(html.Div(), id=_EXPORT_OUTPUT)),
        ]
    )


def _replace_linebreaks(text: str) -> List[Component]:
    return [html.P(line) for line in text.split('\n')]


def _layout() -> Component:
    if not get_current_user().is_authenticated:
        origin = quote_plus(f'/{Endpoint.UPLOAD_AMS}')
        return dcc.Location(pathname=f'/{Endpoint.LOGIN}/{origin}', id='login-redirect')
    return _layout_if_logged()


def _callbacks(app: Dash) -> None:
    @app.callback(Output(_EXPORT_OUTPUT, 'children'), Input(_BUTTON, 'n_clicks'), prevent_initial_call=True)
    def _edit_topic(_):
        try:
            filename = upload_ams()
            bucket = 'https://storage.sbg.cloud.ovh.net/v1/AUTH_3287ea227a904f04ad4e8bceb0776108/am/'
            return html.Div(
                f'AMs exportés avec succès. Nom du fichier créé dans le bucket {bucket} : {filename} ',
                className='alert alert-success',
            )
        except Exception:
            return [
                html.Div('Une erreur est survenue pendant l\'exportation :', className='alert alert-danger'),
                html.Div(_replace_linebreaks(traceback.format_exc()), className='alert alert-danger'),
            ]


PAGE = Page(_layout, _callbacks)
