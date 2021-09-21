from back_office.utils import generate_id

_prefix = 'edit-am-content-new'
AM_ID = generate_id(_prefix, 'am-id')
TEXT_AREA_COMPONENT = generate_id(_prefix, 'text_area-component')
TOC_COMPONENT = generate_id(_prefix, 'toc-component')
FETCH_LEGIFRANCE = generate_id(_prefix, 'fetch-legifrance')
FETCH_AIDA = generate_id(_prefix, 'fetch-aida')
AIDA_LEGIFRANCE_CONFIRM  = generate_id(_prefix, 'aida-legifrance-confirm')
FROM_LEGIFRANCE_OR_AIDA  = generate_id(_prefix, 'from-legifrance-or-aida')
AIDA_LEGIFRANCE_MODAL  = generate_id(_prefix, 'aida-legifrance-modal')
AIDA_LEGIFRANCE_OUTPUT = generate_id(_prefix, 'aida-legifrance-output')
SAVE_BUTTON = generate_id(_prefix, 'save-button')
SAVE_OUTPUT = generate_id(_prefix, 'save-output')
DIFF_BODY = generate_id(_prefix, 'diff-body')
DIFF_MODAL = generate_id(_prefix, 'diff-modal')
DIFF_BUTTON = generate_id(_prefix, 'diff-button')
HIDDEN_BUTTON = generate_id(_prefix, 'hidden-button')  # Only for triggering callback once
SAVE_MODAL_BODY = generate_id(_prefix, 'save-modal-body')
SAVE_MODAL = generate_id(_prefix, 'save-modal')
PRESAVE_BUTTON = generate_id(_prefix, 'presave-button')
