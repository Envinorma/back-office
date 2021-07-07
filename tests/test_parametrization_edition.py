from datetime import date

import pytest
from envinorma.parametrization import AndCondition, Equal, Greater, Littler, OrCondition, ParameterEnum, Range

from back_office.pages.parametrization_edition.condition_form import (
    _AND_ID,
    _CONDITION_VARIABLES,
    _OR_ID,
    _change_to_mono_conditions,
    _get_str_target,
    _make_mono_conditions,
)


def test_change_to_mono_conditions():
    _date = ParameterEnum.DATE_AUTORISATION.value
    _regime = ParameterEnum.REGIME.value
    d1 = date(2010, 1, 1)
    d2 = date(2020, 1, 1)
    res = _change_to_mono_conditions(Range(_date, d1, d2))
    assert res == (_AND_ID, [Littler(_date, d2, True), Greater(_date, d1, False)])

    res = _change_to_mono_conditions(Range(_date, d1, d2, True, True))
    assert res == (_AND_ID, [Littler(_date, d2, True), Greater(_date, d1, True)])

    res = _change_to_mono_conditions(Range(_date, d1, d2, False, False))
    assert res == (_AND_ID, [Littler(_date, d2, False), Greater(_date, d1, False)])

    res = _change_to_mono_conditions(Littler(_date, d1, False))
    assert res == (_AND_ID, [Littler(_date, d1, False)])

    res = _change_to_mono_conditions(Greater(_date, d1, False))
    assert res == (_AND_ID, [Greater(_date, d1, False)])

    input_ = frozenset([Greater(_date, d1, False), Equal(_regime, 'A')])
    op, conditions = _change_to_mono_conditions(OrCondition(input_))
    assert op == _OR_ID
    assert frozenset(conditions) == input_

    with pytest.raises(ValueError):
        _change_to_mono_conditions(OrCondition(frozenset([Range(_date, d1, d2), Equal(_regime, 'A')])))

    op, conditions = _change_to_mono_conditions(AndCondition(frozenset([Range(_date, d1, d2), Equal(_regime, 'A')])))
    assert (op, set(conditions)) == (_AND_ID, {Littler(_date, d2), Greater(_date, d1), Equal(_regime, 'A')})


def test_get_str_target():
    for param in _CONDITION_VARIABLES.values():
        try:
            _get_str_target('test', param.value.type)
        except Exception as exc:
            if 'Unhandled parameter type' in str(exc):
                raise exc


def test_make_mono_conditions():
    d1 = date(2010, 1, 1)
    d2 = date(2020, 1, 1)
    _date = ParameterEnum.DATE_AUTORISATION.value
    res = _make_mono_conditions(Range(_date, d1, d2))
    res == [Littler(_date, d2), Greater(_date, d1)]

    assert _make_mono_conditions(Littler(_date, d2)) == [Littler(_date, d2)]
    assert _make_mono_conditions(Greater(_date, d2)) == [Greater(_date, d2)]
    with pytest.raises(ValueError):
        _make_mono_conditions(AndCondition(frozenset([Greater(_date, d2)])))
