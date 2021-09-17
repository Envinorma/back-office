from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, FrozenSet, List, Optional, Type, Union

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

_AUTORISATION_DATE_FR = 'Date d\'autorisation'
_DECLARATION_DATE_FR = 'Date de déclaration'
_ENREGISTREMENT_DATE_FR = 'Date d\'enregistrement'
_INSTALLATION_DATE_FR = 'Date de mise en service'
CONDITION_VARIABLES = {
    'Régime': ParameterEnum.REGIME,
    _AUTORISATION_DATE_FR: ParameterEnum.DATE_AUTORISATION,
    _DECLARATION_DATE_FR: ParameterEnum.DATE_DECLARATION,
    _ENREGISTREMENT_DATE_FR: ParameterEnum.DATE_ENREGISTREMENT,
    _INSTALLATION_DATE_FR: ParameterEnum.DATE_INSTALLATION,
    'Alinéa': ParameterEnum.ALINEA,
    'Rubrique': ParameterEnum.RUBRIQUE,
    'Quantité associée à la rubrique': ParameterEnum.RUBRIQUE_QUANTITY,
}


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
    if parameter not in CONDITION_VARIABLES:
        raise FormHandlingError(f'Paramètre {parameter} inconnu, attendus: {list(CONDITION_VARIABLES.keys())}')
    return CONDITION_VARIABLES[parameter].value


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


def build_condition(condition_form_values: ConditionFormValues) -> Condition:
    condition_cls = _get_condition_cls(condition_form_values.merge)
    conditions_raw = list(
        zip(condition_form_values.parameters, condition_form_values.operations, condition_form_values.values)
    )
    if len(conditions_raw) == 0:
        raise FormHandlingError('Au moins une condition est nécessaire !')
    conditions = [_extract_condition(i, *condition_raw) for i, condition_raw in enumerate(conditions_raw)]
    return _simplify_condition(condition_cls(frozenset(conditions)))
