import json
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest
from envinorma.models import ArreteMinisteriel, StructuredText
from envinorma.models.text_elements import estr
from envinorma.parametrization import AlternativeSection, AMWarning, InapplicableSection, Littler, ParameterEnum

from back_office.pages.edit_parameter_element.form_handling import (
    FormHandlingError,
    _build_condition,
    _build_new_text,
    _extract_new_parameter_objects,
    _simplify_alineas,
)
from back_office.pages.edit_parameter_element.target_sections_form import TargetSectionFormValues
from back_office.utils import AMOperation, ensure_not_none


def _get_am() -> ArreteMinisteriel:
    subsections = [StructuredText(estr(''), [estr('al1.1.1'), estr('al1.1.2')], [], None)]
    sections = [StructuredText(estr(''), [estr('al1.1'), estr('al1.2')], subsections, None)]
    return ArreteMinisteriel(estr('Arrêté du 10/10/10'), sections, [], None, id='JORFTEXT')


def test_simplify_alineas():
    am = _get_am()
    assert _simplify_alineas(am.sections[0], None) is None
    assert _simplify_alineas(am.sections[0], [0, 1]) is None
    assert _simplify_alineas(am.sections[0], [0]) == [0]
    assert _simplify_alineas(am.sections[0].sections[0], [0]) == [0]
    assert _simplify_alineas(am.sections[0].sections[0], [0, 1]) is None


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


def _littler_condition() -> str:
    return json.dumps(
        {
            'type': 'LITTLER',
            'parameter': {'type': 'DATE', 'id': 'date-d-installation'},
            'target': '2020-01-01',
            'strict': False,
        }
    )


def test_build_condition():
    with pytest.raises(FormHandlingError):
        assert _build_condition("{'erer':'zefze'}")  # ill formed condition

    res = Littler(ParameterEnum.DATE_INSTALLATION.value, date(2020, 1, 1), strict=False)
    assert _build_condition(_littler_condition()) == res


@pytest.fixture
def data_dir() -> Path:
    return Path(__file__).parent / 'data'


@pytest.fixture
def test_am(data_dir: Path) -> ArreteMinisteriel:
    with open(data_dir / 'fake_am.json', 'r') as read_in:
        return ArreteMinisteriel.from_dict(json.load(read_in))


def test_extract_new_parameter_objects_alternative_section(test_am: ArreteMinisteriel):
    operation = AMOperation.ADD_ALTERNATIVE_SECTION
    section_id = test_am.sections[5].sections[0].id
    target = TargetSectionFormValues(['1. Dispositions générales'], ['Lorem ipsum dolor sit amet'], [section_id], [[]])
    condition = _littler_condition()
    warning_content = ''

    new_parameters = _extract_new_parameter_objects(operation, test_am, target, condition, warning_content)
    assert len(new_parameters) == 1
    assert isinstance(new_parameters[0], AlternativeSection)

    new_parameters = _extract_new_parameter_objects(
        operation,
        test_am,
        replace(target, new_texts_titles=['1. Dispositions générales', '2. second paragraph']),
        condition,
        warning_content,
    )
    assert len(new_parameters) == 1
    assert isinstance(new_parameters[0], AlternativeSection)

    new_targets = TargetSectionFormValues(
        ['1. Dispositions générales', '2. second paragraph'],
        ['Lorem ipsum dolor sit amet', 'Lorem ipsum dolor sit amet'],
        [test_am.sections[5].sections[0].id, test_am.sections[5].sections[1].id],
        [[], []],
    )
    new_parameters = _extract_new_parameter_objects(operation, test_am, new_targets, condition, warning_content)
    assert len(new_parameters) == 2
    assert isinstance(new_parameters[0], AlternativeSection)
    assert isinstance(new_parameters[1], AlternativeSection)


def test_extract_new_parameter_objects_condition(test_am: ArreteMinisteriel):
    operation = AMOperation.ADD_CONDITION
    section_id = test_am.sections[5].sections[0].id
    target = TargetSectionFormValues([], [], [section_id], [[10]])
    condition = _littler_condition()
    warning_content = ''

    new_parameters = _extract_new_parameter_objects(operation, test_am, target, condition, warning_content)
    assert len(new_parameters) == 1
    assert isinstance(new_parameters[0], InapplicableSection)

    new_parameters = _extract_new_parameter_objects(
        operation,
        test_am,
        replace(target, target_alineas=[[10], [11]]),
        condition,
        warning_content,
    )
    assert len(new_parameters) == 1
    assert isinstance(new_parameters[0], InapplicableSection)

    ids = [test_am.sections[5].id, test_am.sections[5].sections[1].id]
    new_targets = TargetSectionFormValues([], [], ids, [[0, 2], [0]])
    new_parameters = _extract_new_parameter_objects(operation, test_am, new_targets, condition, warning_content)
    assert len(new_parameters) == 2
    assert isinstance(new_parameters[0], InapplicableSection)
    assert isinstance(new_parameters[1], InapplicableSection)
    assert new_parameters[0].alineas == [0, 2]
    assert new_parameters[1].alineas is None


def test_extract_new_parameter_objects_warning(test_am: ArreteMinisteriel):
    operation = AMOperation.ADD_WARNING
    target = TargetSectionFormValues([], [], [test_am.sections[5].sections[0].id], [])
    warning_content = 'Content of warning.'

    new_parameters = _extract_new_parameter_objects(operation, test_am, target, '', warning_content)
    assert len(new_parameters) == 1
    assert isinstance(new_parameters[0], AMWarning)

    new_parameters = _extract_new_parameter_objects(
        operation,
        test_am,
        replace(target, target_alineas=[[10], [11]]),
        '',
        warning_content,
    )
    assert len(new_parameters) == 1
    assert isinstance(new_parameters[0], AMWarning)

    ids = [test_am.sections[5].id, test_am.sections[5].sections[1].id]
    new_targets = TargetSectionFormValues([], [], ids, [])
    new_parameters = _extract_new_parameter_objects(operation, test_am, new_targets, '', warning_content)
    assert len(new_parameters) == 2
    assert isinstance(new_parameters[0], AMWarning)
    assert isinstance(new_parameters[1], AMWarning)

    with pytest.raises(FormHandlingError):
        new_parameters = _extract_new_parameter_objects(operation, test_am, target, '', 'too short')
