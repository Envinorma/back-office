import json
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest
from envinorma.models import ArreteMinisteriel, Regime, StructuredText, dump_path
from envinorma.models.text_elements import estr
from envinorma.parametrization import (
    AlternativeSection,
    AMWarning,
    AndCondition,
    ConditionSource,
    EntityReference,
    Equal,
    Greater,
    InapplicableSection,
    Littler,
    OrCondition,
    ParameterEnum,
    Range,
    SectionReference,
)

from back_office.pages.parametrization_edition import page_ids
from back_office.pages.parametrization_edition.condition_form import _AND_ID, ConditionFormValues
from back_office.pages.parametrization_edition.form_handling import (
    FormHandlingError,
    _assert_strictly_below,
    _build_condition,
    _build_new_text,
    _build_parameter_value,
    _build_section_reference,
    _build_source,
    _build_target_versions,
    _check_compatibility_and_build_range,
    _extract_new_parameter_objects,
    _extract_parameter_to_conditions,
    _Modification,
    _NotSimplifiableError,
    _simplify_alineas,
    _simplify_condition,
    _simplify_mono_conditions,
    _try_building_range_condition,
)
from back_office.pages.parametrization_edition.target_sections_form import TargetSectionFormValues
from back_office.utils import AMOperation, ensure_not_none


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
    for param in page_ids.CONDITION_VARIABLES.values():
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


def _get_am() -> ArreteMinisteriel:
    subsections = [StructuredText(estr(''), [estr('al1.1.1'), estr('al1.1.2')], [], None)]
    sections = [StructuredText(estr(''), [estr('al1.1'), estr('al1.2')], subsections, None)]
    return ArreteMinisteriel(estr('Arrêté du 10/10/10'), sections, [], None, id='JORFTEXT')


def test_simplify_alineas():
    am = _get_am()
    assert _simplify_alineas(am, SectionReference((0,)), None) is None
    assert _simplify_alineas(am, SectionReference((0,)), [0, 1]) is None
    assert _simplify_alineas(am, SectionReference((0,)), [0]) == [0]
    assert _simplify_alineas(am, SectionReference((0, 0)), [0]) == [0]
    assert _simplify_alineas(am, SectionReference((0, 0)), [0, 1]) is None


def test_build_target_versions():
    am = _get_am()
    form_values = TargetSectionFormValues([], [], [], [])
    assert _build_target_versions(am, form_values) == []

    form_values = TargetSectionFormValues(['title'], ['content'], [dump_path((0, 0))], [])
    text = StructuredText(estr('title'), [estr('content')], [], None)
    modif = _Modification(SectionReference((0, 0)), None, text)
    res = _build_target_versions(am, form_values)
    previous_text: StructuredText = ensure_not_none(res[0].new_text)
    new_text: StructuredText = ensure_not_none(modif.new_text)
    new_text.id = previous_text.id
    assert res == [modif]

    form_values = TargetSectionFormValues([], [], [dump_path((0, 0))], [[0, 1]])
    modif = _Modification(SectionReference((0, 0)), None, None)
    assert _build_target_versions(am, form_values) == [modif]

    form_values = TargetSectionFormValues([], [], [dump_path((0, 0))], [[0]])
    modif = _Modification(SectionReference((0, 0)), [0], None)
    assert _build_target_versions(am, form_values) == [modif]

    form_values = TargetSectionFormValues([], [], [dump_path((0,))], [[0]])
    modif = _Modification(SectionReference((0,)), [0], None)
    assert _build_target_versions(am, form_values) == [modif]


def test_build_new_text():
    assert _build_new_text(None, None) is None
    assert _build_new_text('', '') is None
    with pytest.raises(FormHandlingError):
        _build_new_text('aa', '')
    with pytest.raises(FormHandlingError):
        _build_new_text('', 'bb')
    with pytest.raises(FormHandlingError):
        _build_new_text('aa', None)
    with pytest.raises(FormHandlingError):
        _build_new_text(None, 'bb')
    new_text: StructuredText = ensure_not_none(_build_new_text('aa', 'bb'))
    assert new_text.title.text == 'aa'
    assert new_text.outer_alineas == [estr('bb')]


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


def test_build_source():
    with pytest.raises(FormHandlingError):
        _build_source('')
    assert _build_source('[1, 2]') == ConditionSource(EntityReference(SectionReference((1, 2)), None))


def test_build_section_reference():
    with pytest.raises(FormHandlingError):
        _build_section_reference('')
    assert _build_section_reference('[1, 2, 3]') == SectionReference((1, 2, 3))


@pytest.fixture
def data_dir() -> Path:
    return Path(__file__).parent / 'data'


@pytest.fixture
def test_am(data_dir: Path) -> ArreteMinisteriel:
    with open(data_dir / 'fake_am.json', 'r') as read_in:
        return ArreteMinisteriel.from_dict(json.load(read_in))


def test_extract_new_parameter_objects_alternative_section(test_am: ArreteMinisteriel):
    operation = AMOperation.ADD_ALTERNATIVE_SECTION
    source = '[5]'
    target = TargetSectionFormValues(['1. Dispositions générales'], ['Lorem ipsum dolor sit amet'], ['[5, 0]'], [[]])
    condition = ConditionFormValues(['Date de mise en service'], ['<'], ['01/01/2020'], 'and')
    warning_content = ''

    new_parameters = _extract_new_parameter_objects(operation, test_am, source, target, condition, warning_content)
    assert len(new_parameters) == 1
    assert isinstance(new_parameters[0], AlternativeSection)

    new_parameters = _extract_new_parameter_objects(
        operation,
        test_am,
        source,
        replace(target, new_texts_titles=['1. Dispositions générales', '2. second paragraph']),
        condition,
        warning_content,
    )
    assert len(new_parameters) == 1
    assert isinstance(new_parameters[0], AlternativeSection)

    new_targets = TargetSectionFormValues(
        ['1. Dispositions générales', '2. second paragraph'],
        ['Lorem ipsum dolor sit amet', 'Lorem ipsum dolor sit amet'],
        ['[5, 0]', '[5, 1]'],
        [[], []],
    )
    new_parameters = _extract_new_parameter_objects(operation, test_am, source, new_targets, condition, warning_content)
    assert len(new_parameters) == 2
    assert isinstance(new_parameters[0], AlternativeSection)
    assert isinstance(new_parameters[1], AlternativeSection)

    with pytest.raises(FormHandlingError):
        new_parameters = _extract_new_parameter_objects(operation, test_am, '', target, condition, warning_content)


def test_extract_new_parameter_objects_condition(test_am: ArreteMinisteriel):
    operation = AMOperation.ADD_CONDITION
    source = '[5]'
    target = TargetSectionFormValues([], [], ['[5, 0]'], [[10]])
    condition = ConditionFormValues(['Date de mise en service'], ['<'], ['01/01/2020'], 'and')
    warning_content = ''

    new_parameters = _extract_new_parameter_objects(operation, test_am, source, target, condition, warning_content)
    assert len(new_parameters) == 1
    assert isinstance(new_parameters[0], InapplicableSection)

    new_parameters = _extract_new_parameter_objects(
        operation,
        test_am,
        source,
        replace(target, target_alineas=[[10], [11]]),
        condition,
        warning_content,
    )
    assert len(new_parameters) == 1
    assert isinstance(new_parameters[0], InapplicableSection)

    new_targets = TargetSectionFormValues([], [], ['[5]', '[5, 1]'], [[0, 2], [0]])
    new_parameters = _extract_new_parameter_objects(operation, test_am, source, new_targets, condition, warning_content)
    assert len(new_parameters) == 2
    assert isinstance(new_parameters[0], InapplicableSection)
    assert isinstance(new_parameters[1], InapplicableSection)
    assert new_parameters[0].targeted_entity.outer_alinea_indices == [0, 2]
    assert new_parameters[1].targeted_entity.outer_alinea_indices is None

    with pytest.raises(FormHandlingError):
        new_parameters = _extract_new_parameter_objects(operation, test_am, '', target, condition, warning_content)


def test_extract_new_parameter_objects_warning(test_am: ArreteMinisteriel):
    operation = AMOperation.ADD_WARNING
    source = ''
    target = TargetSectionFormValues([], [], ['[5, 0]'], [])
    condition = ConditionFormValues([], [], [], 'and')
    warning_content = 'Content of warning.'

    new_parameters = _extract_new_parameter_objects(operation, test_am, source, target, condition, warning_content)
    assert len(new_parameters) == 1
    assert isinstance(new_parameters[0], AMWarning)

    new_parameters = _extract_new_parameter_objects(
        operation,
        test_am,
        source,
        replace(target, target_alineas=[[10], [11]]),
        condition,
        warning_content,
    )
    assert len(new_parameters) == 1
    assert isinstance(new_parameters[0], AMWarning)

    new_targets = TargetSectionFormValues([], [], ['[5]', '[5, 1]'], [])
    new_parameters = _extract_new_parameter_objects(operation, test_am, source, new_targets, condition, warning_content)
    assert len(new_parameters) == 2
    assert isinstance(new_parameters[0], AMWarning)
    assert isinstance(new_parameters[1], AMWarning)

    with pytest.raises(FormHandlingError):
        new_parameters = _extract_new_parameter_objects(operation, test_am, '', target, condition, 'too short')
