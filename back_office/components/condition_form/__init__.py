import json
from datetime import date, datetime
from typing import Any, Callable, Dict, List, Optional, Tuple, Union, cast

import dash_bootstrap_components as dbc
from dash import ALL, MATCH, Dash, Input, Output, State, dcc, html
from dash.development.base_component import Component
from envinorma.models import Regime, ensure_rubrique
from envinorma.parametrization import (
    AndCondition,
    Condition,
    Equal,
    Greater,
    Littler,
    MonoCondition,
    OrCondition,
    ParameterEnum,
    ParameterType,
    Range,
    ensure_mono_conditions,
)

from back_office.utils import generate_id

from .helpers import CONDITION_VARIABLES, INSTALLATION_DATE_FR, ConditionFormValues, FormHandlingError, build_condition

_CONDITION_VARIABLE_OPTIONS = [{'label': condition, 'value': condition} for condition in CONDITION_VARIABLES]
_CONDITION_OPERATIONS = ['<', '=', '>=']
_CONDITION_OPERATION_OPTIONS = [{'label': condition, 'value': condition} for condition in _CONDITION_OPERATIONS]
_AND_ID = 'and'
_OR_ID = 'or'
_MERGE_VALUES_OPTIONS = [{'value': _AND_ID, 'label': 'ET'}, {'value': _OR_ID, 'label': 'OU'}]


class _ConditionIds:
    def __init__(self, condition_id: str) -> None:
        self.prefix = condition_id
        self.CONDITION = condition_id
        self.OUTPUT = generate_id(condition_id, 'OUTPUT')
        self.CARD = generate_id(condition_id, 'CARD')
        self.INSTALLATION_DATE_FR = generate_id(condition_id, 'INSTALLATION_DATE_FR')
        self.ADD_CONDITION_BLOCK = generate_id(condition_id, 'ADD_CONDITION_BLOCK')
        self.CONDITION_MERGE = generate_id(condition_id, 'CONDITION_MERGE')
        self.CONDITION_BLOCKS = generate_id(condition_id, 'CONDITION_BLOCKS')
        self.CONDITION_MERGE_AREA = generate_id(condition_id, 'CONDITION_MERGE_AREA')

    def delete_condition_button(self, rank: int) -> Dict[str, Any]:
        return {'id': f'{self.prefix}-delete_condition_button', 'rank': rank}

    def condition_parameter(self, rank: int) -> Dict[str, Any]:
        return {'id': f'{self.prefix}-condition_parameter', 'rank': rank}

    def condition_operation(self, rank: int) -> Dict[str, Any]:
        return {'id': f'{self.prefix}-condition_operation', 'rank': rank}

    def condition_value(self, rank: int) -> Dict[str, Any]:
        return {'id': f'{self.prefix}-condition_value', 'rank': rank}

    def condition_block(self, rank: int) -> Dict[str, Any]:
        return {'id': f'{self.prefix}-condition_block', 'rank': rank}


def _get_str_operation(condition: MonoCondition) -> str:
    if isinstance(condition, Equal):
        return '='
    if isinstance(condition, Greater):
        return '>' if condition.strict else '>='
    if isinstance(condition, Littler):
        return '<' if condition.strict else '<='
    raise NotImplementedError(f'Unknown type {type(condition)}')


def _get_str_variable(condition: MonoCondition) -> str:
    for variable_name, variable in CONDITION_VARIABLES.items():
        if variable.value == condition.parameter:
            return variable_name
    return ''


def _date_to_dmy(date_: Union[date, datetime]) -> str:
    return date_.strftime('%d/%m/%Y')


def _ensure_date(value: Any) -> Union[date, datetime]:
    if isinstance(value, (date, datetime)):
        return value
    raise ValueError(f'Expected type (date, datetime), received type {type(value)}')


def _ensure_regime(value: Any) -> Regime:
    if isinstance(value, Regime):
        return value
    raise ValueError(f'Expected type Regime, received type {type(value)}')


def _ensure_str(value: Any) -> str:
    if isinstance(value, str):
        return value
    raise ValueError(f'Expected type str, received type {type(value)}')


def _ensure_float_(candidate: str) -> float:
    try:
        return float(candidate)
    except ValueError:
        raise ValueError(f'Expected type float, received {candidate} of type {type(candidate)}.')


def _get_str_target(value: Any, parameter_type: ParameterType) -> str:
    if value is None:
        return ''
    if parameter_type == parameter_type.DATE:
        return _date_to_dmy(_ensure_date(value))
    if parameter_type == parameter_type.REGIME:
        return _ensure_regime(value).value
    if parameter_type == parameter_type.REAL_NUMBER:
        return str(_ensure_float_(value))
    if parameter_type == parameter_type.RUBRIQUE:
        return ensure_rubrique(value)
    if parameter_type == parameter_type.STRING:
        return _ensure_str(value)
    raise ValueError(f'Unhandled parameter type: {parameter_type.value}')


def _delete_button(rank: int, ids: _ConditionIds) -> Component:
    return dbc.Button('X', color='light', id=ids.delete_condition_button(rank), size='sm', className='ml-1')


def _parameter_input(rank: int, default_condition: Optional[MonoCondition], ids: _ConditionIds) -> Component:
    default_variable = INSTALLATION_DATE_FR if not default_condition else _get_str_variable(default_condition)
    return dcc.Dropdown(
        id=ids.condition_parameter(rank),
        options=_CONDITION_VARIABLE_OPTIONS,
        clearable=False,
        value=default_variable,
        style={'width': '195px', 'margin-right': '5px'},
        optionHeight=50,
    )


def _operation_input(rank: int, default_condition: Optional[MonoCondition], ids: _ConditionIds) -> Component:
    return dcc.Dropdown(
        id=ids.condition_operation(rank),
        options=_CONDITION_OPERATION_OPTIONS,
        clearable=False,
        value='=' if not default_condition else _get_str_operation(default_condition),
        style={'width': '45px', 'margin-right': '5px'},
    )


def _value_input(rank: int, default_condition: Optional[MonoCondition], ids: _ConditionIds) -> Component:
    default_target = (
        '' if not default_condition else _get_str_target(default_condition.target, default_condition.parameter.type)
    )
    return dcc.Input(
        id=ids.condition_value(rank),
        value=str(default_target),
        type='text',
        className='form-control form-control-sm',
    )


def _add_block_button(ids: _ConditionIds) -> Component:
    txt = '+'
    btn = html.Button(txt, className='mt-2 mb-2 btn btn-light btn-sm', id=ids.ADD_CONDITION_BLOCK)
    return html.Div(btn)


def _condition_block(rank: int, default_condition: Optional[MonoCondition], ids: _ConditionIds) -> Component:
    conditions_block = [
        _parameter_input(rank, default_condition, ids),
        _operation_input(rank, default_condition, ids),
        _value_input(rank, default_condition, ids),
        _delete_button(rank, ids),
    ]
    return html.Div(
        conditions_block,
        className='small-dropdown',
        style={'display': 'flex', 'margin-bottom': '5px'},
        id=ids.condition_block(rank),
    )


def _condition_blocks(default_conditions: Optional[List[MonoCondition]], ids: _ConditionIds) -> Component:
    if default_conditions:
        condition_blocks = [_condition_block(i, cd, ids) for i, cd in enumerate(default_conditions)]
    else:
        condition_blocks = [_condition_block(0, None, ids)]
    return html.Div(condition_blocks, id=ids.CONDITION_BLOCKS)


def _tooltip_content() -> Component:
    return html.Div(
        [
            html.P('Formats :'),
            html.P('- Date : JJ/MM/AAAA'),
            html.P('- Régime : A, E ou D'),
            html.P(
                '- Alinéa : utiliser exactement la même valeur que les alinéas utilisés dans envinorma '
                '(pour consulter les alinéas sur envinorma, il suffit de créer un nouveau classement)'
            ),
        ]
    )


def _get_condition_tooltip() -> Component:
    return html.Div(
        [
            'Conditions ',
            dbc.Badge('?', id='param-edition-conditions-tooltip', pill=True),
            dbc.Tooltip([_tooltip_content()], target='param-edition-conditions-tooltip'),
        ]
    )


def _make_mono_conditions(condition: Condition) -> List[MonoCondition]:
    if isinstance(condition, (Equal, Greater, Littler)):
        return [condition]
    if isinstance(condition, Range):
        return [
            Littler(condition.parameter, condition.right, condition.right_strict),
            Greater(condition.parameter, condition.left, condition.left_strict),
        ]
    raise ValueError(f'Unexpected condition type {type(condition)}')


def _change_to_mono_conditions(condition: Condition) -> Tuple[str, List[MonoCondition]]:
    if isinstance(condition, (Equal, Greater, Littler, Range)):
        return _AND_ID, _make_mono_conditions(condition)
    if isinstance(condition, AndCondition):
        children_mono_conditions = [cd for child in condition.conditions for cd in _make_mono_conditions(child)]
        return _AND_ID, children_mono_conditions
    if isinstance(condition, (AndCondition, OrCondition)):
        return _OR_ID, ensure_mono_conditions(list(condition.conditions))
    raise NotImplementedError(f'Unhandled condition {type(condition)}')


def _merge_input(default_merge: str, ids: _ConditionIds) -> Component:
    merge_dropdown = dcc.Dropdown(
        options=_MERGE_VALUES_OPTIONS, clearable=False, value=default_merge, id=ids.CONDITION_MERGE
    )
    return html.Div(['Opération', merge_dropdown], id=ids.CONDITION_MERGE_AREA)


def _condition_form(default_condition: Optional[Condition], ids: _ConditionIds) -> Component:
    default_conditions: List[MonoCondition] = []
    if default_condition:
        default_merge, default_conditions = _change_to_mono_conditions(default_condition)
    else:
        default_merge = _AND_ID
        default_conditions = [Littler(ParameterEnum.DATE_INSTALLATION.value, None)]
    tooltip = _get_condition_tooltip()
    conditions = html.Div(children=_condition_blocks(default_conditions, ids))
    return dbc.Card(
        [
            dbc.CardBody(
                [_merge_input(default_merge, ids), tooltip, conditions, _add_block_button(ids), html.Div(id=ids.OUTPUT)]
            ),
        ],
        outline=True,
        color='dark',
        class_name='mb-3',
        id=ids.CARD,
    )


def _callbacks(ids: _ConditionIds) -> Callable[[Dash], None]:
    def _add_callbacks(app: Dash):
        @app.callback(
            Output(ids.condition_block(cast(int, MATCH)), 'children'),
            Input(ids.delete_condition_button(cast(int, MATCH)), 'n_clicks'),
            prevent_initial_call=True,
        )
        def delete_section(_):
            return html.Div()

        @app.callback(
            Output(ids.CONDITION_BLOCKS, 'children'),
            Input(ids.ADD_CONDITION_BLOCK, 'n_clicks'),
            State(ids.CONDITION_BLOCKS, 'children'),
            State(ids.condition_block(cast(int, ALL)), 'id'),
            prevent_initial_call=True,
        )
        def add_block(_, children, ranks):
            new_rank = (max([cast(int, id_['rank']) for id_ in ranks]) + 1) if ranks else 0
            new_block = _condition_block(rank=new_rank, default_condition=None, ids=ids)
            return children + [new_block]

        @app.callback(
            Output(ids.CONDITION, 'data'),
            Output(ids.CARD, 'color'),
            Output(ids.OUTPUT, 'children'),
            Input(ids.condition_parameter(cast(int, ALL)), 'value'),
            Input(ids.condition_operation(cast(int, ALL)), 'value'),
            Input(ids.condition_value(cast(int, ALL)), 'value'),
            Input(ids.CONDITION_MERGE, 'value'),
            prevent_initial_call=True,
        )
        def _build_condition(parameters, operations, values, merge):
            condition_form_values = ConditionFormValues(parameters, operations, values, merge)
            try:
                condition = build_condition(condition_form_values)
            except FormHandlingError as exc:
                return ('', 'danger', dbc.Alert(str(exc), color='danger'))
            return (json.dumps(condition.to_dict()), 'success', html.Div())

        @app.callback(
            Output(ids.CONDITION_MERGE_AREA, 'hidden'),
            Input(ids.condition_parameter(cast(int, ALL)), 'value'),
            Input(ids.condition_operation(cast(int, ALL)), 'value'),
            Input(ids.condition_value(cast(int, ALL)), 'value'),
        )
        def _toggle_merge_operation(_, __, values):
            if len(values) > 1:
                return False
            return True

    return _add_callbacks


def condition_form(default_value: Optional[Condition], id: str) -> Component:
    ids = _ConditionIds(id)
    condition_store = dcc.Store(id=ids.CONDITION, data=json.dumps(default_value.to_dict()) if default_value else None)
    return html.Div([_condition_form(default_value, ids), condition_store])


def callbacks(id: str) -> Callable[[Dash], None]:
    ids = _ConditionIds(id)
    return _callbacks(ids)
