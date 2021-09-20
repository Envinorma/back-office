import traceback
from datetime import date
from typing import Any, Dict, List, Optional, Set, Tuple

import dash_bootstrap_components as dbc
from dash import ALL, Dash, Input, Output, State, dcc, html
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
from envinorma.enriching import add_metadata
from envinorma.models import AMMetadata, ArreteMinisteriel, Regime
from envinorma.parametrization import Parameter, ParameterEnum, ParameterType, Parametrization
from envinorma.parametrization.apply_parameter_values import AMWithApplicability, build_am_with_applicability
from envinorma.utils import random_id

from back_office.components import error_component
from back_office.components.parametric_am import parametric_am_callbacks, parametric_am_component
from back_office.utils import DATA_FETCHER, ensure_not_none

_PREFIX = 'am-apply-params'
_AM = _PREFIX + '-am'
_SUBMIT = _PREFIX + '-submit'
_AM_ID = _PREFIX + '-am-id'
_FORM_OUTPUT = _PREFIX + '-form-output'


def _store(parameter_id: Any) -> Dict[str, Any]:
    return {'type': _PREFIX + '-store', 'key': parameter_id}


def _input(parameter_id: Any) -> Dict[str, Any]:
    return {'type': _PREFIX + '-input', 'key': parameter_id}


def _am_component(am: AMWithApplicability) -> Component:
    if not am.arrete.legifrance_url:
        am.arrete = add_metadata(am.arrete, ensure_not_none(DATA_FETCHER.load_am_metadata(am.arrete.id or '')))
    return parametric_am_component(am, _PREFIX)


def _am_component_with_toc(am: Optional[AMWithApplicability]) -> Component:
    if not am:
        warning = 'Choisir un jeu de paramètres pour afficher la version correspondante.'
        component = dbc.Alert(warning, color='warning', className='mb-3 mt-3')
    else:
        component = _am_component(am)
    return html.Div(component, id=_AM)


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


def _am_parameters(am: ArreteMinisteriel) -> Set[Parameter]:
    if not am.applicability.condition_of_inapplicability:
        return set()
    return set(am.applicability.condition_of_inapplicability.parameters())


def _parametrization_form(am: ArreteMinisteriel, parametrization: Parametrization) -> Component:
    parameters = parametrization.extract_parameters().union(_am_parameters(am))
    output = html.Div(
        id=_FORM_OUTPUT,
        style={'margin-top': '10px', 'margin-bottom': '10px'},
        className='col-12',
        hidden=not parameters,
    )
    submit = html.Div(
        html.Button('Valider', className='btn btn-primary', id=_SUBMIT),
        className='col-12',
        style={'margin-top': '10px', 'margin-bottom': '10px'},
    )
    if not parameters:
        components = [html.P('Pas de paramètres pour cet arrêté.')]
    else:
        sorted_parameters = sorted(list(parameters), key=lambda x: x.id)
        components = [_build_parameter_input(parameter) for parameter in sorted_parameters]

    return html.Div([*components, output, submit], className='row g-3')


def _parametrization_component(am_id: str) -> Component:
    parametrization = DATA_FETCHER.load_parametrization(am_id)
    am = DATA_FETCHER.load_am(am_id)
    if not am:
        content = html.Div('Arrêté ministériel inexistent.')
    elif not parametrization:
        content = html.Div('Paramétrage non défini pour cet arrêté.')
    else:
        content = _parametrization_form(am, parametrization)
    return html.Div([html.H2('Paramétrage'), content])


def _form_header(am_id: str) -> Component:
    return _parametrization_component(am_id)


def _layout(am_metadata: AMMetadata) -> Component:
    return html.Div(
        [
            _form_header(am_metadata.cid),
            html.Div(_am_component_with_toc(None)),
            dcc.Store(data=am_metadata.cid, id=_AM_ID),
        ]
    )


def _load_am(am_id: str) -> Optional[ArreteMinisteriel]:
    return DATA_FETCHER.load_am(am_id)


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


def _callbacks(app: Dash, tab_id: str) -> None:
    @app.callback(
        Output(_AM, 'children'),
        Output(_FORM_OUTPUT, 'children'),
        Input(_SUBMIT, 'n_clicks'),
        State(_store(ALL), 'data'),
        State(_input(ALL), 'value'),
        State(_AM_ID, 'data'),
        prevent_initial_call=True,
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
            am_with_applicability = build_am_with_applicability(am, parametrization, parameter_values)
        except _FormError as exc:
            return html.Div(), error_component(str(exc))
        except Exception:
            return html.Div(), error_component(traceback.format_exc())
        return _am_component(am_with_applicability), dbc.Alert('AM filtré.', color='success', dismissable=True)

    parametric_am_callbacks(app, _PREFIX)


TAB = ("Application d'un jeu de paramètres", _layout, _callbacks)
