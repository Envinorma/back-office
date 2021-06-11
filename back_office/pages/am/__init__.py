import traceback
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash import Dash
from dash.dependencies import ALL, Input, Output, State
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
from envinorma.models import AMMetadata, AMState, ArreteMinisteriel, Regime, add_metadata
from envinorma.parametrization import Parameter, ParameterType, Parametrization
from envinorma.parametrization.conditions import ParameterEnum
from envinorma.parametrization.parametric_am import (
    apply_parameter_values_to_am,
    extract_parameters_from_parametrization,
)
from envinorma.utils import random_id

from back_office.components import error_component
from back_office.components.parametric_am import parametric_am_callbacks, parametric_am_component
from back_office.pages.am import am_compare
from back_office.routing import Endpoint, Page
from back_office.utils import DATA_FETCHER, ensure_not_none, get_current_user

_PREFIX = 'display-am'
_AM = _PREFIX + '-am'
_SUBMIT = _PREFIX + '-submit'
_AM_ID = _PREFIX + '-am-id'
_FORM_OUTPUT = _PREFIX + '-form-output'


def _store(parameter_id: Any) -> Dict[str, Any]:
    return {'type': _PREFIX + '-store', 'key': parameter_id}


def _input(parameter_id: Any) -> Dict[str, Any]:
    return {'type': _PREFIX + '-input', 'key': parameter_id}


def _am_component(am: ArreteMinisteriel) -> Component:
    if not am.legifrance_url:
        am = add_metadata(am, ensure_not_none(DATA_FETCHER.load_am_metadata(am.id or '')))
    return parametric_am_component(am, _PREFIX)


def _am_component_with_toc(am: Optional[ArreteMinisteriel]) -> Component:
    if not am:
        return dbc.Alert('404 - AM non initialisé.', color='warning', className='mb-3 mt-3')
    return html.Div(_am_component(am), id=_AM)


def _extract_name(parameter: Parameter) -> str:
    if parameter == ParameterEnum.DATE_AUTORISATION.value:
        return 'Date d\'autorisation'
    if parameter == ParameterEnum.DATE_ENREGISTREMENT.value:
        return 'Date d\'enregistrement'
    if parameter == ParameterEnum.DATE_DECLARATION.value:
        return 'Date de déclaration'
    if parameter == ParameterEnum.DATE_INSTALLATION.value:
        return 'Date de mise en service'
    if parameter == ParameterEnum.REGIME.value:
        return 'Régime'
    if parameter == ParameterEnum.RUBRIQUE.value:
        return 'Rubrique'
    if parameter == ParameterEnum.ALINEA.value:
        return 'Alinéa'
    if parameter == ParameterEnum.RUBRIQUE_QUANTITY.value:
        return 'Quantité associée à la rubrique'
    raise NotImplementedError(parameter)


def _build_input(id_: str, parameter_type: ParameterType) -> Component:
    if parameter_type == ParameterType.BOOLEAN:
        return dbc.Checklist(options=[{'label': '', 'value': 1}], switch=True, value=1, id=_input(id_))
    if parameter_type == ParameterType.DATE:
        return dbc.Input(id=_input(id_), className='form-control', type='date')
    if parameter_type == ParameterType.REGIME:
        options = [{'value': reg.value, 'label': reg.value} for reg in Regime]
        return dcc.Dropdown(options=options, id=_input(id_))
    if parameter_type == ParameterType.RUBRIQUE:
        return dcc.Input(id=_input(id_), className='form-control')
    if parameter_type == ParameterType.REAL_NUMBER:
        return dcc.Input(id=_input(id_), className='form-control')
    if parameter_type == ParameterType.STRING:
        return dcc.Input(id=_input(id_), className='form-control')
    raise NotImplementedError(parameter_type)


def _build_parameter_input(parameter: Parameter) -> Component:
    parameter_name = _extract_name(parameter)
    return html.Div(
        [
            html.Label(parameter_name, htmlFor=(id_ := random_id())),
            _build_input(id_, parameter.type),
            dcc.Store(data=parameter.id, id=_store(parameter.id)),
        ],
        className='col-md-12',
    )


def _parametrization_form(parametrization: Parametrization) -> Component:
    parameters = extract_parameters_from_parametrization(parametrization)
    if not parameters:
        return html.P(
            [
                'Pas de paramètres pour cet arrêté.',
                html.Button(id=_SUBMIT, hidden=True),  # avoid dash error for missing ID
                html.Div(id=_FORM_OUTPUT, hidden=True),  # avoid dash error for missing ID
            ]
        )
    sorted_parameters = sorted(list(parameters), key=lambda x: x.id)
    return html.Div(
        [
            *[_build_parameter_input(parameter) for parameter in sorted_parameters],
            html.Div(
                id=_FORM_OUTPUT,
                style={'margin-top': '10px', 'margin-bottom': '10px'},
                className='col-12',
            ),
            html.Div(
                html.Button('Valider', className='btn btn-primary', id=_SUBMIT),
                className='col-12',
                style={'margin-top': '10px', 'margin-bottom': '10px'},
            ),
        ],
        className='row g-3',
    )


def _parametrization_component(am_id: str) -> Component:
    parametrization = DATA_FETCHER.load_parametrization(am_id)
    if not parametrization:
        content = html.Div('Paramétrage non défini pour cet arrêté.')
    else:
        content = _parametrization_form(parametrization)
    return html.Div([html.H2('Paramétrage'), content])


def _link(text: str, href: str) -> Component:
    return dcc.Link(html.Button(text, className='btn btn-link'), href=href)


def _diff_component(am_id: str) -> Component:
    return html.Div(
        [
            html.H2('Comparer'),
            _link('Avec la version Légifrance', f'/am/{am_id}/compare/legifrance'),
            _link('Avec la version AIDA', f'/am/{am_id}/compare/aida'),
        ]
    )


def _edit_component(am_id: str) -> Component:
    alert = (
        dbc.Alert('Cet arrêté peut être modifié, restructuré ou paramétré par toute personne.')
        if not get_current_user().is_authenticated
        else html.Div()
    )
    return html.Div(
        [
            html.H2('Éditer'),
            alert,
            html.Div(dcc.Link(dbc.Button('Éditer le contenu de l\'arrêté', color='success'), href=f'/edit_am/{am_id}')),
            html.Div(
                dcc.Link(dbc.Button('Supprimer l\'arrêté', color='danger'), href=f'/{Endpoint.DELETE_AM}/{am_id}'),
                className='mt-2',
            ),
        ]
    )


def _form_header(am_id: str, am: Optional[ArreteMinisteriel]) -> Component:
    columns = [
        html.Div(_parametrization_component(am_id), className='col-4') if am else html.Div(),
        html.Div(_diff_component(am_id), className='col-4') if am else html.Div(),
        html.Div(_edit_component(am_id), className='col-4'),
    ]
    return html.Div(columns, className='row')


def _warning(am_metadata: AMMetadata) -> Component:
    if am_metadata.state == AMState.VIGUEUR:
        return html.Div()
    if am_metadata.state == AMState.ABROGE:
        return dbc.Alert(
            'Cet arrêté est abrogé et ne sera pas exploité dans l\'application envinorma.', color='warning'
        )
    if am_metadata.state == AMState.DELETED:
        return dbc.Alert(
            f'Cet arrêté a été supprimé et ne sera pas exploité dans l\'application envinorma. '
            f'Raison de la suppression :\n{am_metadata.reason_deleted}',
            color='warning',
        )
    raise NotImplementedError(f'Unhandled state {am_metadata.state}')


def _page(am_metadata: AMMetadata, am: Optional[ArreteMinisteriel]) -> Component:
    style = {'height': '80vh', 'overflow-y': 'auto'}
    return html.Div(
        [
            _warning(am_metadata),
            _form_header(am_metadata.cid, am),
            html.Div(_am_component_with_toc(am), style=style),
            dcc.Store(data=am_metadata.cid, id=_AM_ID),
        ]
    )


def _load_am(am_id: str) -> Optional[ArreteMinisteriel]:
    return DATA_FETCHER.load_most_advanced_am(am_id)


def _layout(am_id: str, compare_with: Optional[str] = None) -> Component:
    if compare_with:
        return am_compare.layout(am_id, compare_with)
    am_metadata = DATA_FETCHER.load_am_metadata(am_id)
    if not am_metadata:
        return html.Div('404 - AM inexistant.')
    am = _load_am(am_id)
    return _page(am_metadata, am)


class _FormError(Exception):
    pass


def _extract_float(value_str: Optional[str]) -> Optional[float]:
    if not value_str:
        return None
    try:
        return float(value_str)
    except ValueError:
        raise _FormError(f'Erreur dans le formulaire : nombre attendu,  {value_str} reçu')


def _extract_parameter_and_value(id_: str, value: Optional[str]) -> Tuple[Parameter, Any]:
    date_params = (
        ParameterEnum.DATE_AUTORISATION,
        ParameterEnum.DATE_ENREGISTREMENT,
        ParameterEnum.DATE_DECLARATION,
        ParameterEnum.DATE_INSTALLATION,
    )
    for param in date_params:
        if id_ == param.value.id:
            return (param.value, date.fromisoformat(value) if value else None)
    if id_ == ParameterEnum.REGIME.value.id:
        return (ParameterEnum.REGIME.value, Regime(value) if value else None)
    if id_ == ParameterEnum.RUBRIQUE_QUANTITY.value.id:
        return (ParameterEnum.RUBRIQUE_QUANTITY.value, _extract_float(value))
    if id_ == ParameterEnum.RUBRIQUE.value.id:
        return (ParameterEnum.RUBRIQUE.value, value if value else None)
    if id_ == ParameterEnum.ALINEA.value.id:
        return (ParameterEnum.ALINEA.value, value if value else None)
    raise NotImplementedError()


def _extract_parameter_values(ids: List[str], values: List[Optional[str]]) -> Dict[Parameter, Any]:
    values_with_none = dict(_extract_parameter_and_value(id_, value) for id_, value in zip(ids, values))
    return {key: value for key, value in values_with_none.items() if value is not None}


def _callbacks(app: Dash) -> None:
    @app.callback(
        Output(_AM, 'children'),
        Output(_FORM_OUTPUT, 'children'),
        Input(_SUBMIT, 'n_clicks'),
        State(_store(ALL), 'data'),
        State(_input(ALL), 'value'),
        State(_AM_ID, 'data'),
    )
    def _apply_parameters(_, parameter_ids, parameter_values, am_id):
        am = _load_am(am_id)
        if not am:
            raise PreventUpdate
        parametrization = DATA_FETCHER.load_parametrization(am_id)
        if not parametrization:
            raise PreventUpdate
        try:
            parameter_values = _extract_parameter_values(parameter_ids, parameter_values)
            am = apply_parameter_values_to_am(am, parametrization, parameter_values)
        except _FormError as exc:
            return html.Div(), error_component(str(exc))
        except Exception:
            return html.Div(), error_component(traceback.format_exc())
        return _am_component(am), html.Div()

    parametric_am_callbacks(app, _PREFIX)
    am_compare.add_callbacks(app)


PAGE = Page(_layout, _callbacks)
