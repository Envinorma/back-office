import json
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Callable, Dict, FrozenSet, List, Optional, Tuple, Type, Union, cast

import dash_bootstrap_components as dbc
from dash import ALL, MATCH, Dash, Input, Output, State, dcc, html
from dash.development.base_component import Component
from envinorma.models import Regime, ensure_rubrique
from envinorma.models.parameter import Parameter
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

_AUTORISATION_DATE_FR = 'Date d\'autorisation'
_DECLARATION_DATE_FR = 'Date de déclaration'
_ENREGISTREMENT_DATE_FR = 'Date d\'enregistrement'
_INSTALLATION_DATE_FR = 'Date de mise en service'
_CONDITION_VARIABLES = {
    'Régime': ParameterEnum.REGIME,
    _AUTORISATION_DATE_FR: ParameterEnum.DATE_AUTORISATION,
    _DECLARATION_DATE_FR: ParameterEnum.DATE_DECLARATION,
    _ENREGISTREMENT_DATE_FR: ParameterEnum.DATE_ENREGISTREMENT,
    _INSTALLATION_DATE_FR: ParameterEnum.DATE_INSTALLATION,
    'Alinéa': ParameterEnum.ALINEA,
    'Rubrique': ParameterEnum.RUBRIQUE,
    'Quantité associée à la rubrique': ParameterEnum.RUBRIQUE_QUANTITY,
}
_CONDITION_VARIABLE_OPTIONS = [{'label': condition, 'value': condition} for condition in _CONDITION_VARIABLES]
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
    for variable_name, variable in _CONDITION_VARIABLES.items():
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
    default_variable = ids.INSTALLATION_DATE_FR if not default_condition else _get_str_variable(default_condition)
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


def _get_condition_tooltip() -> Component:
    return html.Div(
        [
            'Liste de conditions ',
            dbc.Badge('?', id='param-edition-conditions-tooltip', pill=True),
            dbc.Tooltip(
                ['Formats:', html.Br(), 'Régime: A, E, D ou NC.', html.Br(), 'Date: JJ/MM/AAAA'],
                target='param-edition-conditions-tooltip',
            ),
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
    return html.Div(['Opération', merge_dropdown])


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


@dataclass
class ConditionFormValues:
    parameters: List[str]
    operations: List[str]
    values: List[str]
    merge: str


class FormHandlingError(Exception):
    pass


def _get_condition_cls(merge: str) -> Union[Type[AndCondition], Type[OrCondition]]:
    if merge == 'and':
        return AndCondition
    if merge == 'or':
        return OrCondition
    raise FormHandlingError('Mauvaise opération d\'aggrégation dans le formulaire. Attendu: ET ou OU.')


def _extract_parameter(parameter: str) -> Parameter:
    if parameter not in _CONDITION_VARIABLES:
        raise FormHandlingError(f'Paramètre {parameter} inconnu, attendus: {list(_CONDITION_VARIABLES.keys())}')
    return _CONDITION_VARIABLES[parameter].value


def _parse_dmy(date_str: str) -> date:
    try:
        return datetime.strptime(date_str, '%d/%m/%Y').date()
    except ValueError:
        raise FormHandlingError(f'Date mal formattée. Format attendu JJ/MM/AAAA. Reçu: "{date_str}"')


def _ensure_float(candidate: str) -> float:
    try:
        return float(candidate)
    except ValueError:
        raise FormHandlingError('Valeur incorrecte dans une condition, nombre attendu.')


def _ensure_rubrique(candidate: str) -> str:
    try:
        return ensure_rubrique(candidate)
    except ValueError:
        raise FormHandlingError('Rubrique incorrecte dans une condition, format attendu XXXX')


def _parse_regime(regime_str: str) -> Regime:
    try:
        return Regime(regime_str)
    except ValueError:
        raise FormHandlingError(f'Mauvais régime. Attendu: {[x.value for x in Regime]}. Reçu: "{regime_str}"')


def _build_parameter_value(parameter_type: ParameterType, value_str: str) -> Any:
    if parameter_type == parameter_type.DATE:
        return _parse_dmy(value_str)
    if parameter_type == parameter_type.REGIME:
        return _parse_regime(value_str)
    if parameter_type == parameter_type.REAL_NUMBER:
        return _ensure_float(value_str)
    if parameter_type == parameter_type.RUBRIQUE:
        return _ensure_rubrique(value_str)
    if parameter_type == parameter_type.STRING:
        return value_str
    raise FormHandlingError(f'Ce type de paramètre n\'est pas géré: {parameter_type.value}')


def _extract_condition(rank: int, parameter: str, operator: str, value_str: str) -> Condition:
    try:
        built_parameter = _extract_parameter(parameter)
        value = _build_parameter_value(built_parameter.type, value_str)
    except FormHandlingError as exc:
        raise FormHandlingError(f'Erreur dans la {rank+1}{"ère" if rank == 0 else "ème"} condition: {exc}')
    if operator == '<':
        return Littler(built_parameter, value, True)
    if operator == '<=':
        return Littler(built_parameter, value, False)
    if operator == '>':
        return Greater(built_parameter, value, True)
    if operator == '>=':
        return Greater(built_parameter, value, False)
    if operator == '=':
        return Equal(built_parameter, value)
    raise FormHandlingError(f'La {rank+1}{"ère" if rank == 0 else "ème"} condition contient un opérateur inattendu.')


def _assert_greater_condition(condition: Condition) -> Greater:
    if not isinstance(condition, Greater):
        raise ValueError(f'Expecting type Greater, got {type(condition)}')
    return condition


def _assert_littler_condition(condition: Condition) -> Littler:
    if not isinstance(condition, Littler):
        raise ValueError(f'Expecting type Greater, got {type(condition)}')
    return condition


def _assert_strictly_below(small_candidate: Any, great_candidate: Any) -> None:
    if isinstance(small_candidate, (datetime, date, float, int)):
        if small_candidate >= great_candidate:
            raise FormHandlingError('Erreur dans les conditions: les deux conditions sont incompatibles.')


def _check_compatibility_and_build_range(
    parameter: Parameter, condition_1: MonoCondition, condition_2: MonoCondition
) -> Range:
    if isinstance(condition_1, Equal) or isinstance(condition_2, Equal):
        raise FormHandlingError('Erreur dans les conditions. Elles sont soit redondantes, soit incompatibles.')
    if isinstance(condition_1, Littler) and isinstance(condition_2, Littler):
        raise FormHandlingError('Erreur dans les conditions. Elles sont redondantes.')
    if isinstance(condition_1, Greater) and isinstance(condition_2, Greater):
        raise FormHandlingError('Erreur dans les conditions. Elles sont redondantes.')
    if isinstance(condition_1, Littler):
        littler_condition = condition_1
        greater_condition = _assert_greater_condition(condition_2)
    else:
        littler_condition = _assert_littler_condition(condition_2)
        greater_condition = _assert_greater_condition(condition_1)
    littler_target = littler_condition.target
    greater_target = greater_condition.target
    _assert_strictly_below(greater_target, littler_target)
    return Range(parameter, greater_target, littler_target)


def _extract_parameter_to_conditions(conditions: List[MonoCondition]) -> Dict[Parameter, List[MonoCondition]]:
    res: Dict[Parameter, List[MonoCondition]] = {}
    for condition in conditions:
        if condition.parameter not in res:
            res[condition.parameter] = []
        res[condition.parameter].append(condition)
    return res


class _NotSimplifiableError(Exception):
    pass


def _simplify_mono_conditions(parameter: Parameter, conditions: List[MonoCondition]) -> Union[MonoCondition, Range]:
    if len(conditions) >= 3 or len(conditions) == 0:
        raise _NotSimplifiableError()
    if len(conditions) == 1:
        return conditions[0]
    if parameter.type not in (ParameterType.DATE, ParameterType.REAL_NUMBER):
        raise FormHandlingError('Erreur dans les conditions: elles sont soit incompatibles, soit redondantes.')
    return _check_compatibility_and_build_range(parameter, conditions[0], conditions[1])


def _try_building_range_condition(conditions: FrozenSet[Condition]) -> Optional[Condition]:
    if not conditions:
        return None
    mono_conditions = ensure_mono_conditions(list(conditions))
    parameter_to_conditions = _extract_parameter_to_conditions(mono_conditions)
    try:
        new_conditions = [_simplify_mono_conditions(param, cds) for param, cds in parameter_to_conditions.items()]
    except _NotSimplifiableError:
        return None
    return AndCondition(frozenset(new_conditions)) if len(new_conditions) != 1 else new_conditions[0]


def _simplify_condition(condition: Condition) -> Condition:
    if isinstance(condition, (AndCondition, OrCondition)):
        if len(condition.conditions) == 1:
            return list(condition.conditions)[0]
        if len(condition.conditions) == 0:
            raise FormHandlingError('Au moins une condition est nécessaire !')
    if isinstance(condition, AndCondition):
        potential_range_condition = _try_building_range_condition(condition.conditions)
        if potential_range_condition:
            return potential_range_condition
    return condition


def _build_condition(condition_form_values: ConditionFormValues) -> Condition:  # TODO: move
    condition_cls = _get_condition_cls(condition_form_values.merge)
    conditions_raw = list(
        zip(condition_form_values.parameters, condition_form_values.operations, condition_form_values.values)
    )
    if len(conditions_raw) == 0:
        raise FormHandlingError('Au moins une condition est nécessaire !')
    conditions = [_extract_condition(i, *condition_raw) for i, condition_raw in enumerate(conditions_raw)]
    return _simplify_condition(condition_cls(frozenset(conditions)))


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
        def build_condition(parameters, operations, values, merge):
            condition_form_values = ConditionFormValues(parameters, operations, values, merge)
            try:
                condition = _build_condition(condition_form_values)
            except FormHandlingError as exc:
                return ('', 'danger', dbc.Alert(str(exc), color='danger'))
            return (json.dumps(condition.to_dict()), 'success', html.Div())

    return _add_callbacks


def condition_form(default_value: Optional[Condition], id: str) -> Component:
    ids = _ConditionIds(id)
    condition_store = dcc.Store(id=ids.CONDITION, data=json.dumps(default_value.to_dict()) if default_value else None)
    return html.Div([_condition_form(default_value, ids), condition_store])


def callbacks(id: str) -> Callable[[Dash], None]:
    ids = _ConditionIds(id)
    return _callbacks(ids)
