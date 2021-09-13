from dataclasses import replace
from typing import Optional
from urllib.parse import quote_plus

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, dcc, html
from dash.development.base_component import Component
from envinorma.models import DELETE_REASON_MIN_NB_CHARS, AMMetadata, AMState

from back_office.helpers.login import get_current_user
from back_office.pages.parametrization_edition.form_handling import FormHandlingError
from back_office.routing import Endpoint, Page
from back_office.utils import DATA_FETCHER, generate_id

_DELETE_REASON = generate_id(__file__, 'delete-reason')
_AM_ID = generate_id(__file__, 'am-id')
_FORM_OUTPUT = generate_id(__file__, 'form-output')
_SUCCESS_REDIRECT = generate_id(__file__, 'success-redirect')
_SUBMIT_DELETION = generate_id(__file__, 'submit-deletion')


def _delete_form(am_id: str) -> Component:
    return html.Div(
        [
            html.Label(
                f'Raison de la suppression (minimum {DELETE_REASON_MIN_NB_CHARS} caractères) :', className='form-label'
            ),
            dcc.Input(value='', id=_DELETE_REASON, className='form-control'),
            dcc.Store(data=am_id, id=_AM_ID),
            html.Div(id=_FORM_OUTPUT),
            html.Button('Supprimer l\'AM', className='btn btn-primary mt-2 mb-2', id=_SUBMIT_DELETION),
        ]
    )


def _page_if_logged(am_id: str) -> Component:
    am_metadata = DATA_FETCHER.load_am_metadata(am_id)
    if not am_metadata:
        return html.H1('Arrêté introuvable.')
    return html.Div([html.H2(f'Suppression de l\'arrêté {am_id}'), html.P(am_metadata.title), _delete_form(am_id)])


def _page(am_id: str) -> Component:
    if not get_current_user().is_authenticated:
        origin = quote_plus(f'/{Endpoint.DELETE_AM}/{am_id}')
        return dcc.Location(pathname=f'/{Endpoint.LOGIN}/{origin}', id='login-redirect')
    return _page_if_logged(am_id)


def _get_and_check_am(am_id: str) -> AMMetadata:
    res = DATA_FETCHER.load_am_metadata(am_id)
    if not res:
        raise FormHandlingError(f'L\'arrêté {am_id} n\'existe pas.')
    if res.state != AMState.VIGUEUR:
        raise FormHandlingError(f'L\'arrêté {am_id} est déjà supprimé')
    return res


def _check_delete_reason(delete_reason: str) -> None:
    if len(delete_reason) <= DELETE_REASON_MIN_NB_CHARS:
        raise FormHandlingError(
            f'Le raison de la suppression doit comporter au moins {DELETE_REASON_MIN_NB_CHARS} caractères.'
        )


def _upsert_am(am_metadata: AMMetadata, delete_reason: str) -> None:
    am_metadata = replace(am_metadata)
    am_metadata.state = AMState.DELETED
    am_metadata.reason_deleted = delete_reason
    DATA_FETCHER.upsert_am(am_metadata)


def _handle_form(am_id: str, delete_reason: str) -> None:
    am_metadata = _get_and_check_am(am_id)
    _check_delete_reason(delete_reason)
    _upsert_am(am_metadata, delete_reason)


def _handle_submit_deletion(am_id: str, delete_reason: str) -> Component:
    try:
        _handle_form(am_id, delete_reason)
    except FormHandlingError as exc:
        return dbc.Alert(f'Erreur dans le formulaire: {exc}', color='danger', dismissable=True, className='mt-2 mb-2')
    return html.Div(
        [
            dbc.Alert('Suppression réussie.', color='success', dismissable=True, className='mt-2 mb-2'),
            dcc.Location(pathname=f'/{Endpoint.AM}/{am_id}', id=_SUCCESS_REDIRECT),
        ]
    )


def _add_callbacks(app: dash.Dash) -> None:
    @app.callback(
        Output(_FORM_OUTPUT, 'children'),
        Input(_SUBMIT_DELETION, 'n_clicks'),
        State(_AM_ID, 'data'),
        State(_DELETE_REASON, 'value'),
        prevent_initial_call=True,
    )
    def handle_submit_deletion(_, am_id: str, delete_reason: Optional[str]) -> Component:
        return _handle_submit_deletion(am_id, delete_reason or '')


PAGE = Page(_page, _add_callbacks, True)
