import traceback
from datetime import date
from typing import Any, Dict, List, Optional, Set, Tuple

import dash_bootstrap_components as dbc
from dash import ALL, Dash, Input, Output, State, callback_context, dcc, html, no_update
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
from envinorma.enriching import add_metadata
from envinorma.models import ArreteMinisteriel, Regime
from envinorma.parametrization import Parameter, ParameterEnum, ParameterType, Parametrization
from envinorma.parametrization.apply_parameter_values import AMWithApplicability, build_am_with_applicability
from envinorma.utils import random_id

from back_office.components import error_component
from back_office.components.am_side_nav import page_with_sidebar
from back_office.components.parametric_am import parametric_am_callbacks, parametric_am_component
from back_office.routing import Page
from back_office.utils import DATA_FETCHER, ensure_not_none

_PREFIX = 'am-apply-params'
_AM = _PREFIX + '-am'
_SUBMIT = _PREFIX + '-submit'
_AM_ID = _PREFIX + '-am-id'
_FORM_OUTPUT = _PREFIX + '-form-output'
_FORM = _PREFIX + '-form'
_DISPLAY_FORM_BUTTON = _PREFIX + '-display-form-button'
_HIDE_FORM_BUTTON = _PREFIX + '-hide-form-button'


def _store(parameter_id: Any) -> Dict[str, Any]:
    return {'type': _PREFIX + '-store', 'key': parameter_id}


def _input(parameter_id: Any) -> Dict[str, Any]:
    return {'type': _PREFIX + '-input', 'key': parameter_id}


def _am_component(am: AMWithApplicability) -> Component:
    if not am.arrete.legifrance_url:
        am.arrete = add_metadata(am.arrete, ensure_not_none(DATA_FETCHER.load_am_metadata(am.arrete.id or '')))
    return parametric_am_component(am, _PREFIX, with_topics=False)


def _am_component_with_toc(am: Optional[AMWithApplicability]) -> Component:
    component = _am_component(am) if am else html.Div()
    return html.Div(dbc.Spinner(component), id=_AM)


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
        ]
    )


def _am_parameters(am: ArreteMinisteriel) -> Set[Parameter]:
    if not am.applicability.condition_of_inapplicability:
        return set()
    return set(am.applicability.condition_of_inapplicability.parameters())


def _parameters(parameters: Set[Parameter]) -> Component:
    if not parameters:
        return html.P('Pas de paramètres pour cet arrêté.')
    sorted_parameters = sorted(list(parameters), key=lambda x: x.id)
    warning = 'Choisir un jeu de paramètres pour afficher la version correspondante.'
    component = dbc.Alert(warning, color='warning', className='mb-3 mt-3')
    return html.Div([component, *[_build_parameter_input(parameter) for parameter in sorted_parameters]])


def _parametrization_form(am: Optional[ArreteMinisteriel], parametrization: Parametrization) -> Component:
    parameters = parametrization.extract_parameters().union(_am_parameters(am) if am else set())
    submit = html.Div(html.Button('Valider', className='btn btn-primary', id=_SUBMIT), className='m-2')
    output = html.Div('', id=_FORM_OUTPUT, className='m-2')
    return html.Div([_parameters(parameters), output, submit])


def _parametrization_component(am_id: str, hidden: bool) -> Component:
    parametrization = DATA_FETCHER.load_or_init_parametrization(am_id)
    am = DATA_FETCHER.load_am(am_id)
    content = _parametrization_form(am, parametrization)
    if not am:
        content = html.Div([html.Div('Arrêté ministériel non initialisé.'), html.Div(content, hidden=True)])
    return html.Div([html.H3('Paramétrage'), content, html.Hr()], hidden=hidden, id=_FORM)


def _display_form_button() -> Component:
    return html.Div(
        [
            html.Button('< Retour', id=_HIDE_FORM_BUTTON, className='btn btn-link float-start', hidden=True),
            html.Button('Filtrer par paramètres', id=_DISPLAY_FORM_BUTTON, className='btn btn-primary'),
        ],
        style={'text-align': 'right', 'flex': True},
    )


def _main_component(am_id: str, hidden: bool) -> Component:
    am_metadata = DATA_FETCHER.load_am_metadata(am_id)
    if not am_metadata:
        return html.Div('Arrêté ministériel inexistant.')
    return html.Div(
        [
            _display_form_button(),
            html.Hr(className='mb-4'),
            _parametrization_component(am_metadata.cid, hidden),
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


def _display_trigger() -> bool:
    if not callback_context.triggered:
        return False
    return _DISPLAY_FORM_BUTTON in callback_context.triggered[0]['prop_id']


def _callbacks(app: Dash) -> None:
    @app.callback(
        Output(_FORM, 'hidden'),
        Output(_HIDE_FORM_BUTTON, 'hidden'),
        Input(_DISPLAY_FORM_BUTTON, 'n_clicks'),
        Input(_HIDE_FORM_BUTTON, 'n_clicks'),
        State(_FORM, 'hidden'),
        State(_HIDE_FORM_BUTTON, 'hidden'),
        prevent_initial_call=True,
    )
    def _display_form(_, __, hidden, hidden_):
        return not hidden, not hidden_

    @app.callback(
        Output(_AM, 'children'),
        Output(_FORM_OUTPUT, 'children'),
        Input(_SUBMIT, 'n_clicks'),
        Input(_DISPLAY_FORM_BUTTON, 'n_clicks'),
        State(_store(ALL), 'data'),
        State(_input(ALL), 'value'),
        State(_AM_ID, 'data'),
    )
    def _apply_parameters(_, __, parameter_ids, parameter_values, am_id):
        if _display_trigger():
            return no_update, html.Div('')
        am = _load_am(am_id)
        if not am:
            raise PreventUpdate
        parametrization = DATA_FETCHER.load_or_init_parametrization(am_id)
        try:
            parameter_values = _extract_parameter_values(parameter_ids, parameter_values)
            am_with_applicability = build_am_with_applicability(am, parametrization, parameter_values)
        except _FormError as exc:
            return html.Div(), error_component(str(exc))
        except Exception:
            return html.Div(), error_component(traceback.format_exc())
        return _am_component(am_with_applicability), dbc.Alert('AM filtré.', color='success', dismissable=True)

    parametric_am_callbacks(app, _PREFIX)


def _layout(am_id: str) -> Component:
    return page_with_sidebar(html.Div([_main_component(am_id, True), dcc.Store(data=am_id, id=_AM_ID)]), am_id)


PAGE = Page(_layout, _callbacks, False)
