from typing import List, Optional, Union

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
from back_office.routing import Page
from back_office.utils import DATA_FETCHER, AMOperation, RouteParsingError

from . import page_ids
from .form import add_callbacks, form

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
    destination_rank: int,
    loaded_parameter: Optional[ParameterObject],
) -> Component:
    text = am.to_text()
    border_style = {'padding': '10px', 'border': '1px solid rgba(0,0,0,.1)', 'border-radius': '5px'}
    am_component_ = am_component(am, emphasized_words=_EMPHASIZED_WORDS, first_level=3)
    cols = [
        html.Div(
            form(am.id or '', text, operation, loaded_parameter, destination_rank),
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
    am_id: str,
    destination_rank: int,
    loaded_parameter: Optional[ParameterObject],
) -> Component:
    hidden_components = [
        html.P(am_id, hidden=True, id=page_ids.AM_ID),
        html.P(operation.value, hidden=True, id=page_ids.AM_OPERATION),
        html.P(destination_rank, hidden=True, id=page_ids.PARAMETER_RANK),
    ]
    page = _get_main_component(am, operation, destination_rank, loaded_parameter)

    return html.Div([page, *hidden_components], className='parametrization_content')


def _load_am(am_id: str) -> Optional[ArreteMinisteriel]:
    return DATA_FETCHER.load_most_advanced_am(am_id)


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


def _router(am_id: str, operation: AMOperation, rank: Optional[str] = None, copy: bool = False) -> Component:
    rank_int = int(rank) if rank is not None else None
    try:
        am_metadata = DATA_FETCHER.load_am_metadata(am_id)
        if not am_metadata:
            return html.P('404 - Arrêté inconnu')
        am = _load_am(am_id)
        parametrization = DATA_FETCHER.load_or_init_parametrization(am_id)
        loaded_parameter = _get_parameter(parametrization, operation, rank_int) if rank_int is not None else None
    except RouteParsingError as exc:
        return html.P(f'404 - Page introuvable - {str(exc)}')
    if not am or not parametrization or not am_metadata:
        return html.P(f'404 - Arrêté {am_id} introuvable.')
    if rank_int is not None and not copy:
        destination_rank = rank_int
    else:
        destination_rank = -1
    return _build_page(am, operation, am_id, destination_rank, loaded_parameter)


def _router_condition(am_id: str, rank: Optional[str] = None, copy: bool = False):
    return _router(am_id, AMOperation.ADD_CONDITION, rank, copy)


def _router_alternative_section(am_id: str, rank: Optional[str] = None, copy: bool = False):
    return _router(am_id, AMOperation.ADD_ALTERNATIVE_SECTION, rank, copy)


def _router_warning(am_id: str, rank: Optional[str] = None, copy: bool = False):
    return _router(am_id, AMOperation.ADD_WARNING, rank, copy)


PAGE_CONDITION = Page(_router_condition, add_callbacks, True)
# TODO: replace lambda x: None when switching to new callbacks
PAGE_ALTERNATIVE_SECTION = Page(_router_alternative_section, lambda x: None, True)
PAGE_WARNING = Page(_router_warning, lambda x: None, True)
