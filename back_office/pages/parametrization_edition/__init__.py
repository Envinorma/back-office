from typing import List, Optional, Tuple, Union

from dash import html
from dash.development.base_component import Component
from envinorma.models import ArreteMinisteriel
from envinorma.parametrization import (
    AlternativeSection,
    AMWarning,
    InapplicableSection,
    ParameterObject,
    Parametrization,
)

from back_office.components.am_component import am_component
from back_office.routing import build_am_page
from back_office.utils import DATA_FETCHER, AMOperation, RouteParsingError

from . import page_ids
from .form import form

_EMPHASIZED_WORDS = [
    'déclaration',
    'enregistrement',
    'autorisation',
    'application',
    'alinéa',
    'installations existantes',
    'appliquent',
    'applicables',
    'applicable',
]


def _get_main_component(
    am: ArreteMinisteriel,
    operation: AMOperation,
    am_page: str,
    destination_rank: int,
    loaded_parameter: Optional[ParameterObject],
) -> Component:
    text = am.to_text()
    border_style = {'padding': '10px', 'border': '1px solid rgba(0,0,0,.1)', 'border-radius': '5px'}
    am_component_ = am_component(am, emphasized_words=_EMPHASIZED_WORDS, first_level=3)
    cols = [
        html.Div(
            form(text, operation, am_page, loaded_parameter, destination_rank),
            className='col-5',
        ),
        html.Div(
            am_component_,
            className='col-7',
            style={'overflow-y': 'auto', 'position': 'sticky', 'height': '90vh', **border_style},
        ),
    ]
    return html.Div(cols, className='row')


def _build_page(
    am: ArreteMinisteriel,
    operation: AMOperation,
    am_page: str,
    am_id: str,
    destination_rank: int,
    loaded_parameter: Optional[ParameterObject],
) -> Component:
    hidden_components = [
        html.P(am_id, hidden=True, id=page_ids.AM_ID),
        html.P(operation.value, hidden=True, id=page_ids.AM_OPERATION),
        html.P(destination_rank, hidden=True, id=page_ids.PARAMETER_RANK),
    ]
    page = _get_main_component(am, operation, am_page, destination_rank, loaded_parameter)

    return html.Div([page, *hidden_components], className='parametrization_content')


def _load_am(am_id: str) -> Optional[ArreteMinisteriel]:
    return DATA_FETCHER.load_most_advanced_am(am_id)


def _parse_route(route: str) -> Tuple[str, AMOperation, Optional[int], bool]:
    pieces = route.split('/')[1:]
    if len(pieces) <= 1:
        raise RouteParsingError(f'Error parsing route {route}')
    am_id = pieces[0]
    try:
        operation = AMOperation(pieces[1])
    except ValueError:
        raise RouteParsingError(f'Error parsing route {route}')
    if len(pieces) == 2:
        return am_id, operation, None, False
    try:
        parameter_rank = int(pieces[2])
    except ValueError:
        raise RouteParsingError(f'Error parsing route {route}')
    if len(pieces) == 3:
        return am_id, operation, parameter_rank, False
    if pieces[3] != 'copy':
        raise RouteParsingError(f'Error parsing route {route}')
    return am_id, operation, parameter_rank, True


def _get_parameter(parametrization: Parametrization, operation_id: AMOperation, parameter_rank: int) -> ParameterObject:
    parameters: Union[List[AlternativeSection], List[InapplicableSection], List[AMWarning]]
    if operation_id == operation_id.ADD_ALTERNATIVE_SECTION:
        parameters = parametrization.alternative_sections
    elif operation_id == operation_id.ADD_CONDITION:
        parameters = parametrization.inapplicable_sections
    elif operation_id == operation_id.ADD_WARNING:
        parameters = parametrization.warnings
    else:
        raise NotImplementedError(f'{operation_id.value}')
    if parameter_rank >= len(parameters):
        raise RouteParsingError(f'Parameter with rank {parameter_rank} not found.')
    return parameters[parameter_rank]


def router(pathname: str) -> Component:
    try:
        am_id, operation_id, parameter_rank, copy = _parse_route(pathname)
        am_metadata = DATA_FETCHER.load_am_metadata(am_id)
        if not am_metadata:
            return html.P('404 - Arrêté inconnu')
        am_page = build_am_page(am_id)
        am = _load_am(am_id)
        parametrization = DATA_FETCHER.load_or_init_parametrization(am_id)
        loaded_parameter = (
            _get_parameter(parametrization, operation_id, parameter_rank) if parameter_rank is not None else None
        )
    except RouteParsingError as exc:
        return html.P(f'404 - Page introuvable - {str(exc)}')
    if not am or not parametrization or not am_metadata:
        return html.P(f'404 - Arrêté {am_id} introuvable.')
    if parameter_rank is not None and not copy:
        destination_parameter_rank = parameter_rank
    else:
        destination_parameter_rank = -1
    return _build_page(am, operation_id, am_page, am_id, destination_parameter_rank, loaded_parameter)
