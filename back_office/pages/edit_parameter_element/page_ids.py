from typing import Any, Dict


def new_text(rank: int) -> Dict[str, Any]:
    return {'id': 'param-edition-new-text', 'rank': rank}


def new_text_title(rank: int) -> Dict[str, Any]:
    return {'id': 'param-edition-new-text-title', 'rank': rank}


def new_text_content(rank: int) -> Dict[str, Any]:
    return {'id': 'param-edition-new-text-content', 'rank': rank}


def target_section(rank: int) -> Dict[str, Any]:
    return {'id': 'param-edition-target-section', 'rank': rank}


def target_section_store(rank: int) -> Dict[str, Any]:
    return {'id': 'param-edition-target-section-store', 'rank': rank}


def target_alineas(rank: int) -> Dict[str, Any]:
    return {'id': 'param-edition-target-alineas', 'rank': rank}


def propagate_in_subsection(rank: int) -> Dict[str, Any]:
    return {'id': 'param-edition-propagate-subsection', 'rank': rank}


def delete_block_button(rank: int) -> Dict[str, Any]:
    return {'id': 'param-edition-delete-block-button', 'rank': rank}


def delete_condition_button(rank: int) -> Dict[str, Any]:
    return {'id': 'param-edition-delete-condition-button', 'rank': rank}


def target_section_block(rank: int) -> Dict[str, Any]:
    return {'id': 'param-edition-target-section-block', 'rank': rank}


def condition_parameter(rank: int) -> Dict[str, Any]:
    return {'id': 'param-edition-condition-parameter', 'rank': rank}


def condition_operation(rank: int) -> Dict[str, Any]:
    return {'id': 'param-edition-condition-operation', 'rank': rank}


def condition_value(rank: int) -> Dict[str, Any]:
    return {'id': 'param-edition-condition-value', 'rank': rank}


def condition_block(rank: int) -> Dict[str, Any]:
    return {'id': 'param-edition-condition-block', 'rank': rank}


DROPDOWN_OPTIONS = 'param-edition-dropdown-options'
TARGET_BLOCKS = 'param-edition-target-blocks'
ADD_TARGET_BLOCK = 'param-edition-add-target-block'
WARNING_CONTENT = 'param-edition-warning-content'
CONDITION = 'param-edition-condition'
AM_ID = 'param-edition-am-id'
PARAMETER_ID = 'param-edition-param-id'
AM_OPERATION = 'param-edition-am-operation'
