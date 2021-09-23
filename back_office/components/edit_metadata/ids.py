from typing import Any, Dict

from back_office.utils import generate_id

LEGIFRANCE_ID = generate_id(__file__, 'legifrance-id')
SUBMIT_LEGIFRANCE_ID = generate_id(__file__, 'submit-legifrance-id')
SUBMIT_LEGIFRANCE_OUTPUT = generate_id(__file__, 'submit-legifrance-output')
AM_ID = generate_id(__file__, 'am-id')
FORM_OUTPUT = generate_id(__file__, 'form-output')
REFRESH_REDIRECT = generate_id(__file__, 'refresh-redirect')
TITLE = generate_id(__file__, 'title')
NICKNAME = generate_id(__file__, 'nickname')
IS_TRANSVERSE_CHECKBOX = generate_id(__file__, 'is-transverse-checkbox')
AIDA_PAGE = generate_id(__file__, 'aida-page')
ADD_CLASSEMENT_FORM = generate_id(__file__, 'add-classement-form')
CLASSEMENTS = generate_id(__file__, 'classements')
AM_STATE = generate_id(__file__, 'am-state')
AM_SOURCE = generate_id(__file__, 'am-source')
NOR_EXISTS = generate_id(__file__, 'nor-exists')
NOR_ID = generate_id(__file__, 'nor-id')
NOR_DIV = generate_id(__file__, 'nor-div')
REASON_DELETED = generate_id(__file__, 'reason-deleted')
SUBMIT_BUTTON = generate_id(__file__, 'submit-button')
SUCCESS_REDIRECT = generate_id(__file__, 'success-redirect')
REASON_DELETED_DIV = generate_id(__file__, 'reason-deleted-div')


def delete_classement_button_id(rank: int) -> Dict[str, Any]:
    return {'id': generate_id(__file__, 'delete_classement_button_id'), 'rank': rank}


def rubrique_input_id(rank: int) -> Dict[str, Any]:
    return {'id': generate_id(__file__, 'rubrique_input_id'), 'rank': rank}


def regime_id(rank: int) -> Dict[str, Any]:
    return {'id': generate_id(__file__, 'regime_id'), 'rank': rank}


def alinea_input_id(rank: int) -> Dict[str, Any]:
    return {'id': generate_id(__file__, 'alinea_input_id'), 'rank': rank}


def classement_row_id(rank: int) -> Dict[str, Any]:
    return {'id': generate_id(__file__, 'classement_id'), 'rank': rank}
