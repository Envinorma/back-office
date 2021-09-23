import json
import traceback
from dataclasses import dataclass
from typing import Dict, List, Optional

from envinorma.models import ArreteMinisteriel, StructuredText
from envinorma.models.condition import load_condition
from envinorma.models.text_elements import EnrichedString, Table
from envinorma.parametrization import AlternativeSection, AMWarning, Condition, InapplicableSection, ParameterElement

from back_office.helpers.parse_table import parse_table
from back_office.pages.edit_parameter_element.target_sections_form import TargetSectionFormValues
from back_office.utils import DATA_FETCHER, AMOperation, ensure_not_none


class FormHandlingError(Exception):
    pass


def _build_condition(condition: Optional[str]) -> Condition:
    if not condition:
        raise FormHandlingError('La condition doit être définie.')
    try:
        return load_condition(json.loads(condition))
    except Exception:
        raise FormHandlingError(
            f'Erreur inattendue dans la condition :\n{condition}\n' f'Erreur complète :\n{traceback.format_exc()}'
        )


@dataclass
class _Modification:
    section_id: str
    target_alineas: Optional[List[int]]
    new_text: Optional[StructuredText]
    propagate_in_subsection: Optional[bool]


def _parse_table(element: str) -> EnrichedString:
    try:
        result = parse_table(element)
    except ValueError as exc:
        raise FormHandlingError(str(exc))
    if isinstance(result, Table):
        return EnrichedString('', table=result)
    if isinstance(result, str):
        return EnrichedString(result)
    raise ValueError(f'Impossible de parser {element}')


def _extract_alineas(text: str) -> List[EnrichedString]:
    return [_parse_table(line) for line in text.split('\n')]


_MIN_NB_CHARS = 1


def _check_and_build_new_text(title: str, content: str) -> StructuredText:
    if len(title or '') < _MIN_NB_CHARS:
        raise FormHandlingError(f'Le champ "Titre" doit contenir au moins {_MIN_NB_CHARS} caractères.')
    if len(content or '') < _MIN_NB_CHARS:
        raise FormHandlingError(f'Le champ "Contenu du paragraphe" doit contenir au moins {_MIN_NB_CHARS} caractères.')
    return StructuredText(EnrichedString(title), _extract_alineas(content), [], None)


def _build_new_text(new_text_title: Optional[str], new_text_content: Optional[str]) -> Optional[StructuredText]:
    if not new_text_title and not new_text_content:
        return None
    if new_text_title and not new_text_content:
        raise FormHandlingError('Le champ "Contenu du paragraphe" doit être défini.')
    if new_text_content and not new_text_title:
        raise FormHandlingError('Le champ "Titre" doit être défini.')
    return _check_and_build_new_text(new_text_title or '', new_text_content or '')


def _simplify_alineas(section: StructuredText, target_alineas: Optional[List[int]]) -> Optional[List[int]]:
    if not target_alineas:
        return None
    if len(set(target_alineas)) == len(section.outer_alineas):
        return None
    return target_alineas


def _build_target_version(
    section_id_to_section: Dict[str, StructuredText],
    new_text_title: Optional[str],
    new_text_content: Optional[str],
    section_id: str,
    target_alineas: Optional[List[int]],
    propagate_in_subsection: Optional[bool],
) -> _Modification:
    if not section_id:
        raise FormHandlingError('La section visée doit être sélectionnée.')
    if section_id not in section_id_to_section:
        raise FormHandlingError(f'La section "{section_id}" n\'existe pas.')
    section = section_id_to_section[section_id]
    simplified_target_alineas = _simplify_alineas(section, target_alineas)
    new_text = _build_new_text(new_text_title, new_text_content)
    return _Modification(section_id, simplified_target_alineas, new_text, propagate_in_subsection)


def _build_target_versions(am: ArreteMinisteriel, form_values: TargetSectionFormValues) -> List[_Modification]:
    new_texts_titles = form_values.new_texts_titles or len(form_values.target_sections) * [None]
    new_texts_contents = form_values.new_texts_contents or len(form_values.target_sections) * [None]
    target_sections = form_values.target_sections
    target_alineas = form_values.target_alineas or len(form_values.target_sections) * [None]
    propagate_in_subsection = form_values.propagate_in_subsection or len(form_values.target_sections) * [None]
    section_id_to_section = {section.id: section for section in am.descendent_sections()}
    return [
        _build_target_version(section_id_to_section, title, content, section, alineas, propagate_in_subsection)
        for title, content, section, alineas, propagate_in_subsection in zip(
            new_texts_titles, new_texts_contents, target_sections, target_alineas, propagate_in_subsection
        )
    ]


def _build_inapplicable_section(condition: Condition, modification: _Modification) -> InapplicableSection:
    return InapplicableSection(
        modification.section_id,
        modification.target_alineas,
        condition=condition,
        subsections_are_inapplicable=modification.propagate_in_subsection
        if modification.propagate_in_subsection is not None
        else True,
    )


def _build_am_warning(section_id: str, warning_content: str) -> AMWarning:
    min_len = 10
    if len(warning_content or '') <= min_len:
        raise FormHandlingError(f'Le champ "Contenu de l\'avertissement" doit contenir au moins {min_len} caractères.')
    return AMWarning(section_id, warning_content)


def _build_parameter_object(
    operation: AMOperation,
    condition: Optional[Condition],
    modification: _Modification,
    warning_content: str,
) -> ParameterElement:
    if operation == AMOperation.ADD_ALTERNATIVE_SECTION:
        return AlternativeSection(
            section_id=modification.section_id,
            new_text=ensure_not_none(modification.new_text),
            condition=ensure_not_none(condition),
        )
    if operation == AMOperation.ADD_CONDITION:
        return _build_inapplicable_section(ensure_not_none(condition), modification)
    if operation == AMOperation.ADD_WARNING:
        return _build_am_warning(modification.section_id, warning_content)
    raise NotImplementedError(f'Not implemented for operation {operation}')


def _extract_new_parameter_objects(
    operation: AMOperation,
    am: ArreteMinisteriel,
    target_section_form_values: TargetSectionFormValues,
    condition_str: Optional[str],
    warning_content: str,
) -> List[ParameterElement]:
    condition = _build_condition(condition_str) if operation != AMOperation.ADD_WARNING else None
    target_versions = _build_target_versions(am, target_section_form_values)
    return [
        _build_parameter_object(operation, condition, target_version, warning_content)
        for target_version in target_versions
    ]


def _check_consistency(operation: AMOperation, parameters: List[ParameterElement]) -> None:
    for parameter in parameters:
        if operation == AMOperation.ADD_CONDITION:
            assert isinstance(parameter, InapplicableSection), f'Expect InapplicableSection, got {type(parameter)}'
        elif operation == AMOperation.ADD_ALTERNATIVE_SECTION:
            assert isinstance(parameter, AlternativeSection), f'Expect AlternativeSection, got {type(parameter)}'
        elif operation == AMOperation.ADD_WARNING:
            assert isinstance(parameter, AMWarning), f'Expect AMWarning, got {type(parameter)}'
        else:
            raise ValueError(f'Unexpected operation {operation}')


def extract_and_upsert_new_parameter(
    operation: AMOperation,
    am_id: str,
    parameter_id: Optional[str],
    target_section_form_values: TargetSectionFormValues,
    condition: Optional[str],
    warning_content: str,
) -> None:
    am = DATA_FETCHER.load_am(am_id)
    if not am:
        raise ValueError(f'AM with id {am_id} not found!')
    new_parameters = _extract_new_parameter_objects(
        operation, am, target_section_form_values, condition, warning_content
    )
    _check_consistency(operation, new_parameters)
    _upsert_parameters(am_id, new_parameters, parameter_id)


def _upsert_parameters(am_id: str, new_parameters: List[ParameterElement], parameter_id: Optional[str]):
    if parameter_id is not None:
        if len(new_parameters) != 1:
            raise ValueError('Must have only one parameter when updating a specific parameter..')
        DATA_FETCHER.upsert_parameter(am_id, new_parameters[0], parameter_id)
    else:
        for parameter in new_parameters:
            DATA_FETCHER.upsert_parameter(am_id, parameter, None)
