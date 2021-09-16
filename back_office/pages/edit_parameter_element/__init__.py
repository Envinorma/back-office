from typing import List, Optional, Union

from dash import dcc, html
from dash.development.base_component import Component
from envinorma.models import ArreteMinisteriel
from envinorma.parametrization import (
    AlternativeSection,
    AMWarning,
    InapplicableSection,
    ParameterObject,
    Parametrization,
)

from back_office.routing import Page
from back_office.utils import DATA_FETCHER, AMOperation, RouteParsingError

from . import page_ids
from .form import add_callbacks, parameter_element_form


def _get_main_component(
    am: ArreteMinisteriel,
    operation: AMOperation,
    destination_id: Optional[str],
    loaded_parameter: Optional[ParameterObject],
) -> Component:
    return parameter_element_form(am.id or '', am, operation, loaded_parameter, destination_id)


def _build_page(
    am: ArreteMinisteriel,
    operation: AMOperation,
    am_id: str,
    destination_id: Optional[str],
    loaded_parameter: Optional[ParameterObject],
) -> Component:
    hidden_components = [
        dcc.Store(data=am_id, id=page_ids.AM_ID),
        dcc.Store(data=operation.value, id=page_ids.AM_OPERATION),
        dcc.Store(data=destination_id, id=page_ids.PARAMETER_ID),
    ]
    page = _get_main_component(am, operation, destination_id, loaded_parameter)

    return html.Div([page, *hidden_components], className='parametrization_content')


def _load_am(am_id: str) -> Optional[ArreteMinisteriel]:
    return DATA_FETCHER.load_most_advanced_am(am_id)


def _get_parameter(parametrization: Parametrization, operation_id: AMOperation, parameter_id: str) -> ParameterObject:
    parameters: Union[List[AlternativeSection], List[InapplicableSection], List[AMWarning]]
    if operation_id == operation_id.ADD_ALTERNATIVE_SECTION:
        parameters = parametrization.alternative_sections
    elif operation_id == operation_id.ADD_CONDITION:
        parameters = parametrization.inapplicable_sections
    elif operation_id == operation_id.ADD_WARNING:
        parameters = parametrization.warnings
    else:
        raise NotImplementedError(f'{operation_id.value}')
    id_to_parameter = {parameter.id: parameter for parameter in parameters}
    if parameter_id not in id_to_parameter:
        raise RouteParsingError(f'Parameter with id {parameter_id} not found.')
    return id_to_parameter[parameter_id]


def _router(am_id: str, operation: AMOperation, parameter_id: Optional[str] = None, copy: bool = False) -> Component:
    try:
        am_metadata = DATA_FETCHER.load_am_metadata(am_id)
        if not am_metadata:
            return html.P('404 - Arrêté inconnu')
        am = _load_am(am_id)
        parametrization = DATA_FETCHER.load_or_init_parametrization(am_id)
        loaded_parameter = (
            _get_parameter(parametrization, operation, parameter_id) if parameter_id is not None else None
        )
    except RouteParsingError as exc:
        return html.P(f'404 - Page introuvable - {str(exc)}')
    if not am or not parametrization or not am_metadata:
        return html.P(f'404 - Arrêté {am_id} introuvable.')
    if copy:
        parameter_id = None
    return _build_page(am, operation, am_id, parameter_id, loaded_parameter)


def _router_condition(am_id: str, parameter_id: Optional[str] = None, copy: bool = False):
    return _router(am_id, AMOperation.ADD_CONDITION, parameter_id, copy)


def _router_alternative_section(am_id: str, parameter_id: Optional[str] = None, copy: bool = False):
    return _router(am_id, AMOperation.ADD_ALTERNATIVE_SECTION, parameter_id, copy)


def _router_warning(am_id: str, parameter_id: Optional[str] = None, copy: bool = False):
    return _router(am_id, AMOperation.ADD_WARNING, parameter_id, copy)


PAGE_CONDITION = Page(_router_condition, add_callbacks, True)
# replace lambda x: None when switching to new callbacks
PAGE_ALTERNATIVE_SECTION = Page(_router_alternative_section, lambda x: None, True)
PAGE_WARNING = Page(_router_warning, lambda x: None, True)
