from datetime import date

import pytest
from envinorma.models import Regime
from envinorma.parametrization import AndCondition, Equal, Greater, Littler, OrCondition, ParameterEnum, Range

from back_office.components.condition_form import (
    _AND_ID,
    _CONDITION_VARIABLES,
    ConditionFormValues,
    FormHandlingError,
    _assert_strictly_below,
    _build_condition,
    _build_parameter_value,
    _check_compatibility_and_build_range,
    _extract_parameter_to_conditions,
    _NotSimplifiableError,
    _simplify_condition,
    _simplify_mono_conditions,
    _try_building_range_condition,
)


def test_simplify_condition():
    _date = ParameterEnum.DATE_AUTORISATION.value
    _regime = ParameterEnum.REGIME.value
    d1 = date(2010, 1, 1)
    d2 = date(2020, 1, 1)
    with pytest.raises(FormHandlingError):
        _simplify_condition(AndCondition(frozenset()))
    with pytest.raises(FormHandlingError):
        _simplify_condition(OrCondition(frozenset()))
    cond = Greater(_date, d1, False)
    cond_2 = Greater(_date, d2, False)
    assert _simplify_condition(OrCondition(frozenset((cond,)))) == cond
    assert _simplify_condition(AndCondition(frozenset((cond,)))) == cond
    and_cond = AndCondition(frozenset((cond, cond_2)))
    with pytest.raises(FormHandlingError):
        _simplify_condition(and_cond)

    cond_1 = Greater(_date, d1)
    cond_2 = Littler(_date, d1)
    and_cond = AndCondition(frozenset((cond_1, cond_2)))
    with pytest.raises(FormHandlingError):
        _simplify_condition(and_cond)

    cond_1 = Littler(_date, d1)
    cond_2 = Littler(_date, d2)
    and_cond = AndCondition(frozenset((cond_1, cond_2)))
    with pytest.raises(FormHandlingError):
        _simplify_condition(and_cond)

    cond_1 = Littler(_date, d1)
    cond_2 = Equal(_date, d1)
    and_cond = AndCondition(frozenset((cond_1, cond_2)))
    with pytest.raises(FormHandlingError):
        _simplify_condition(and_cond)

    cond_1 = Littler(_date, d2)
    cond_2 = Greater(_date, d1)
    and_cond = AndCondition(frozenset((cond_1, cond_2)))
    res = _simplify_condition(and_cond)
    assert res == Range(_date, d1, d2)

    and_cond = AndCondition(frozenset((Littler(_date, d2), Greater(_date, d1), Equal(_regime, 'A'))))
    res = _simplify_condition(and_cond)
    assert res == AndCondition(frozenset((Range(_date, d1, d2), Equal(_regime, 'A'))))


def test_check_compatibility_and_build_range_try():
    d1 = date(2010, 1, 1)
    d2 = date(2020, 1, 1)

    _date = ParameterEnum.DATE_AUTORISATION.value
    cond_1 = Littler(_date, d2)
    cond_2 = Greater(_date, d1)
    assert isinstance(_check_compatibility_and_build_range(_date, cond_1, cond_2), Range)

    _date = ParameterEnum.DATE_AUTORISATION.value
    cond_1 = Littler(_date, d2)
    cond_2 = Greater(_date, d2)
    with pytest.raises(FormHandlingError):
        _check_compatibility_and_build_range(_date, cond_1, cond_2)


def test_building_range_condition():
    d1 = date(2010, 1, 1)
    d2 = date(2020, 1, 1)
    date_ = ParameterEnum.DATE_AUTORISATION.value
    quantity = ParameterEnum.RUBRIQUE_QUANTITY.value
    reg = ParameterEnum.REGIME.value

    assert _try_building_range_condition(frozenset()) is None

    with pytest.raises(ValueError):
        _try_building_range_condition(frozenset((AndCondition(frozenset()),)))

    with pytest.raises(ValueError):
        _try_building_range_condition(frozenset((OrCondition(frozenset()),)))

    assert _try_building_range_condition(frozenset([Greater(date_, d1, False)])) == Greater(date_, d1, False)

    res = _try_building_range_condition(frozenset([Equal(reg, 'A'), Greater(date_, d2)]))
    assert res == AndCondition(frozenset([Equal(reg, 'A'), Greater(date_, d2)]))

    with pytest.raises(FormHandlingError):
        _try_building_range_condition(frozenset([Littler(date_, d2), Greater(date_, d2)]))

    res = _try_building_range_condition(frozenset([Littler(date_, d2), Greater(date_, d1)]))
    assert res == Range(date_, d1, d2)

    res = _try_building_range_condition(
        frozenset([Littler(date_, d2), Greater(date_, d1), Equal(reg, 'E'), Equal(quantity, 10)])
    )
    assert res == AndCondition(frozenset([Range(date_, d1, d2), Equal(reg, 'E'), Equal(quantity, 10)]))

    res = _try_building_range_condition(frozenset([Littler(quantity, 20), Greater(quantity, 10), Equal(reg, 'D')]))
    assert res == AndCondition(frozenset([Range(quantity, 10, 20), Equal(reg, 'D')]))


def test_simplify_mono_conditions():
    d1 = date(2010, 1, 1)
    d2 = date(2020, 1, 1)
    d3 = date(2030, 1, 1)
    date_ = ParameterEnum.DATE_AUTORISATION.value
    quantity = ParameterEnum.RUBRIQUE_QUANTITY.value
    reg = ParameterEnum.REGIME.value

    with pytest.raises(_NotSimplifiableError):
        _simplify_mono_conditions(date_, [])

    with pytest.raises(_NotSimplifiableError):
        _simplify_mono_conditions(date_, [Equal(date_, d1), Equal(date_, d2), Equal(date_, d3)])

    res = _simplify_mono_conditions(quantity, [Littler(quantity, 100), Greater(quantity, 10)])
    assert res == Range(quantity, 10, 100)

    with pytest.raises(FormHandlingError):
        _simplify_mono_conditions(reg, [Littler(quantity, 10), Greater(quantity, 100)])

    assert _simplify_mono_conditions(date_, [Littler(date_, d1)]) == Littler(date_, d1)
    assert _simplify_mono_conditions(date_, [Greater(date_, d1)]) == Greater(date_, d1)
    assert _simplify_mono_conditions(date_, [Equal(date_, d1)]) == Equal(date_, d1)


def test_assert_strictly_below():
    d1 = date(2010, 1, 1)
    d2 = date(2020, 1, 1)

    with pytest.raises(FormHandlingError):
        _assert_strictly_below(1, 1)
    with pytest.raises(FormHandlingError):
        _assert_strictly_below(2, 1)
    assert _assert_strictly_below(1, 2) is None

    with pytest.raises(FormHandlingError):
        _assert_strictly_below(d1, d1)
    with pytest.raises(FormHandlingError):
        _assert_strictly_below(d2, d1)
    assert _assert_strictly_below(d1, d2) is None


def test_build_parameter_value():
    for param in _CONDITION_VARIABLES.values():
        try:
            _build_parameter_value(param.value.type, '')
        except Exception as exc:
            if 'Ce type de paramètre' in str(exc):
                raise exc


def test_extract_parameter_to_conditions():
    d1 = date(2010, 1, 1)
    d2 = date(2020, 1, 1)
    _date = ParameterEnum.DATE_AUTORISATION.value
    _regime = ParameterEnum.REGIME.value

    res = _extract_parameter_to_conditions([Littler(_date, d2), Greater(_date, d1), Equal(_regime, 'A')])
    assert res == {_date: [Littler(_date, d2), Greater(_date, d1)], _regime: [Equal(_regime, 'A')]}
    res = _extract_parameter_to_conditions([Littler(_date, d2), Greater(_date, d1)])
    assert res == {_date: [Littler(_date, d2), Greater(_date, d1)]}
    res = _extract_parameter_to_conditions([Greater(_date, d1), Equal(_regime, 'A')])
    assert res == {_date: [Greater(_date, d1)], _regime: [Equal(_regime, 'A')]}
    res = _extract_parameter_to_conditions([Greater(_date, d1)])
    assert res == {_date: [Greater(_date, d1)]}
    res = _extract_parameter_to_conditions([])
    assert res == {}


def test_build_condition():
    with pytest.raises(FormHandlingError):
        assert _build_condition(ConditionFormValues([], [], [], _AND_ID))

    res = Equal(ParameterEnum.DATE_DECLARATION.value, date(2020, 1, 1))
    assert _build_condition(ConditionFormValues(['Date de déclaration'], ['='], ['01/01/2020'], _AND_ID)) == res

    res = Range(ParameterEnum.DATE_DECLARATION.value, date(2020, 1, 1), date(2020, 1, 31))
    form_values = ConditionFormValues(['Date de déclaration'] * 2, ['>=', '<'], ['01/01/2020', '31/01/2020'], _AND_ID)
    assert _build_condition(form_values) == res

    cd_1 = Equal(ParameterEnum.DATE_DECLARATION.value, date(2020, 1, 1))
    cd_2 = Equal(ParameterEnum.REGIME.value, Regime.A)
    res = AndCondition(frozenset([cd_1, cd_2]))
    form_values = ConditionFormValues(['Date de déclaration', 'Régime'], ['=', '='], ['01/01/2020', 'A'], _AND_ID)
    assert _build_condition(form_values) == res
