import traceback
from typing import Callable, Tuple

import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, html
from dash.development.base_component import Component

from back_office.components import error_component
from back_office.helpers.upload_ams import upload_ams
from back_office.utils import generate_id

_BUTTON = generate_id('upload-ams', 'trigger-upload')
_EXPORT_OUTPUT = generate_id('upload-ams', 'export-output')
_CANCEL_BUTTON = generate_id('upload-ams', 'cancel-button')
_PROGRESS_BAR = generate_id('upload-ams', 'progress-bar')


def _buttons() -> Component:
    export = html.Button('Exporter les AMs', id=_BUTTON, className='btn btn-primary')
    cancel = html.Button('Annuler', id=_CANCEL_BUTTON, className='btn btn-danger ml-2', hidden=True)
    return html.Div([export, cancel], className='mb-3')


def _explanation() -> Component:
    sentences = [
        'Pour mettre à jour les AM sur l’application Envinorma, exporter les AM dans OVH (environ 2 minutes). Puis ',
        html.A('suivre la documentation', href='https://envinorma.github.io/data/am'),
        '. Seuls les arrêtés ministériels en vigueur sont exportés.',
    ]
    return html.P(sentences)


def upload_ams_component() -> Component:
    return html.Div(
        [
            _explanation(),
            _buttons(),
            dbc.Progress(id=_PROGRESS_BAR, min=0, max=100, value=5, animated=True, className='d-none'),
            html.Div(id=_EXPORT_OUTPUT),
        ]
    )


def upload_ams_callbacks(app: Dash) -> None:
    @app.long_callback(
        output=Output(_EXPORT_OUTPUT, 'children'),
        inputs=Input(_BUTTON, 'n_clicks'),
        running=[
            (Output(_BUTTON, 'disabled'), True, False),
            (Output(_CANCEL_BUTTON, 'hidden'), False, True),
            (Output(_PROGRESS_BAR, 'className'), '', 'd-none'),
        ],
        cancel=[Input(_CANCEL_BUTTON, 'n_clicks')],
        progress=[Output(_PROGRESS_BAR, 'value')],
        prevent_initial_call=True,
    )
    def _callback(set_progress: Callable[[Tuple[int]], None], _):
        set_progress((5,))
        try:
            filename = upload_ams(set_progress)
            bucket = 'https://storage.sbg.cloud.ovh.net/v1/AUTH_3287ea227a904f04ad4e8bceb0776108/am/'
            return html.Div(
                f'AMs exportés avec succès. Nom du fichier créé dans le bucket {bucket} : {filename} ',
                className='alert alert-success',
            )
        except Exception:
            return [
                error_component('Une erreur est survenue pendant l\'exportation :'),
                error_component(traceback.format_exc()),
            ]
