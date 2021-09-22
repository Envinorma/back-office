import json
from typing import Any, Dict, List, Optional, cast

import dash_bootstrap_components as dbc
from dash import ALL, Dash, Input, Output, State, dcc, html
from dash.dependencies import MATCH
from dash.development.base_component import Component
from envinorma.models import Condition
from envinorma.models.am_applicability import AMApplicability
from envinorma.models.condition import load_condition

from back_office.components import error_component, success_component
from back_office.components.condition_form import callbacks, condition_form
from back_office.routing import Endpoint, Page
from back_office.utils import DATA_FETCHER, generate_id

_PREFIX = __file__


class _FormHandlingError(Exception):
    pass


class _Ids:
    ADD_WARNING_FORM = generate_id(_PREFIX, 'add-warning-form')
    WARNINGS = generate_id(_PREFIX, 'warnings')
    SUBMIT_BUTTON = generate_id(_PREFIX, 'submit')
    AM_ID = generate_id(_PREFIX, 'am-id')
    FORM_OUTPUT = generate_id(_PREFIX, 'form-output')
    CONDITION = generate_id(_PREFIX, 'condition')
    CONDITION_DIV = generate_id(_PREFIX, 'condition-div')
    USE_CONDITION = generate_id(_PREFIX, 'use-condition')

    @staticmethod
    def delete_warning_button(rank: int) -> Dict[str, Any]:
        return {'id': generate_id(_PREFIX, 'delete-warning-button'), 'rank': rank}

    @staticmethod
    def warning(rank: int) -> Dict[str, Any]:
        return {'id': generate_id(_PREFIX, 'warning'), 'rank': rank}

    @staticmethod
    def warning_input(rank: int) -> Dict[str, Any]:
        return {'id': generate_id(_PREFIX, 'warning-input'), 'rank': rank}


def _warning_input(warning: Optional[str], rank: int) -> Component:
    return dcc.Input(
        id=_Ids.warning_input(rank),
        value=warning or '',
        type='text',
        placeholder='Cet arrêté ne s\'applique que...',
        className='form-control mr-3',
    )


def _delete_warning_button(rank: int) -> Component:
    return dbc.Button('X', color='light', id=_Ids.delete_warning_button(rank), size='sm', className='ml-1')


def _warning_row(warning: Optional[str], rank: int) -> Component:
    classement_elements = [_warning_input(warning, rank), _delete_warning_button(rank)]
    return html.Div(classement_elements, style={'display': 'flex'}, id=_Ids.warning(rank), className='mb-3')


def _warnings_form(warnings: List[str]) -> Component:
    return html.Div(
        [
            html.H4('Avertissements'),
            html.Div(
                [_warning_row(classement, rank) for rank, classement in enumerate(warnings)],
                id=_Ids.WARNINGS,
            ),
            html.Button('+ Nouvel avertissement', id=_Ids.ADD_WARNING_FORM, className='btn btn-light btn-sm mt-1'),
        ],
        className='mb-3',
    )


def _submit_button() -> Component:
    return html.Button('Valider', className='btn btn-primary', id=_Ids.SUBMIT_BUTTON)


def _buttons() -> Component:
    return html.Div(_submit_button(), className='mb-5')


def _checkbox(checked: bool) -> Component:
    return html.Div(
        dbc.Checkbox(value=checked, id=_Ids.USE_CONDITION, label='Définir la condition d\'inapplicabilité ?'),
        className='mb-3',
    )


def _condition_form(condition: Optional[Condition]) -> Component:
    return html.Div(
        [
            html.H4('Condition d\'inapplicabilité'),
            _checkbox(condition is not None),
            html.Div(condition_form(condition, id=_Ids.CONDITION), id=_Ids.CONDITION_DIV),
        ]
    )


def _form(am_id: str, applicability: AMApplicability) -> Component:
    return html.Div(
        [
            _warnings_form(applicability.warnings),
            _condition_form(applicability.condition_of_inapplicability),
            html.Div(id=_Ids.FORM_OUTPUT),
            _buttons(),
            dcc.Store(data=am_id, id=_Ids.AM_ID),
        ]
    )


def _cancel_button(am_id: Optional[str]) -> Component:
    hidden = not am_id
    return dcc.Link(
        html.Button('< Retour', className='btn btn-link', hidden=hidden),
        href=f'/{Endpoint.EDIT_PARAMETRIZATION}/{am_id}',
    )


def _page(am_id: str) -> Component:
    am = DATA_FETCHER.load_am(am_id)
    if not am:
        return html.Div('AM introuvable')
    btn = _cancel_button(am_id)
    title = html.H3(f'Editer les paramètres d\'application de l\'arrêté ministériel {am_id}.')
    return html.Div([btn, title, _form(am_id, am.applicability)], className='container mt-3')


def _applicability(warnings: List[str], use_condition: bool, condition_str: Optional[str]) -> AMApplicability:
    if use_condition and not condition_str:
        raise _FormHandlingError('La condition d\'inapplicabilité n\'est pas définie.')
    condition = load_condition(json.loads(condition_str or '')) if use_condition else None
    return AMApplicability(warnings, condition)


def _handle_form(warnings: List[str], use_condition: bool, condition: Optional[str], am_id: str) -> Component:
    try:
        new_applicability = _applicability(warnings, use_condition, condition)
        am = DATA_FETCHER.load_am(am_id)
        if not am:
            raise _FormHandlingError('AM introuvable. Impossible d\'enregistrer le formulaire.')
        am.applicability = new_applicability
        DATA_FETCHER.upsert_am(am_id, am)
    except _FormHandlingError as exc:
        return error_component(f"Erreur dans le formulaire : {exc}")
    redirect = dcc.Location(id='am-applicability-redirect', href=f'/{Endpoint.EDIT_PARAMETRIZATION}/{am_id}')
    return html.Div([success_component('Enregistré avec succès.'), redirect])


def _add_callbacks(app: Dash) -> None:
    @app.callback(
        Output(_Ids.FORM_OUTPUT, 'children'),
        Input(_Ids.SUBMIT_BUTTON, 'n_clicks'),
        State(_Ids.warning_input(cast(int, ALL)), 'value'),
        State(_Ids.USE_CONDITION, 'value'),
        State(_Ids.CONDITION, 'data'),
        State(_Ids.AM_ID, 'data'),
        prevent_initial_call=True,
    )
    def handle_form(_, warnings, use_condition, condition, am_id):
        return _handle_form(warnings, use_condition, condition, am_id)

    @app.callback(
        Output(_Ids.CONDITION_DIV, 'hidden'),
        Input(_Ids.USE_CONDITION, 'value'),
    )
    def toggle_condition(checkbox_value):
        return not checkbox_value

    @app.callback(
        Output(_Ids.warning(cast(int, MATCH)), 'children'),
        Input(_Ids.delete_warning_button(cast(int, MATCH)), 'n_clicks'),
        prevent_initial_call=True,
    )
    def delete_section(_):
        return html.Div()

    @app.callback(
        Output(_Ids.WARNINGS, 'children'),
        Input(_Ids.ADD_WARNING_FORM, 'n_clicks'),
        State(_Ids.WARNINGS, 'children'),
        State(_Ids.warning(cast(int, ALL)), 'id'),
        prevent_initial_call=True,
    )
    def add_warning(_, children, ids):
        new_rank = (max([cast(int, id_['rank']) for id_ in ids]) + 1) if ids else 0
        new_block = _warning_row(None, rank=new_rank)
        return children + [new_block]

    callbacks(_Ids.CONDITION)(app)


PAGE = Page(_page, _add_callbacks, True)
