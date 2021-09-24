from back_office.pages.edit_parameter_element.form import _title
from back_office.utils import AMOperation


def test_title():
    # Test all operations are handled
    for operation in AMOperation:
        try:
            _title(operation, True, '')
            _title(operation, False, None)
        except ValueError:
            pass  # This exception occurs for some operations

    assert _title(AMOperation.ADD_ALTERNATIVE_SECTION, False, None) == 'Nouvelle section alternative'
    assert _title(AMOperation.ADD_CONDITION, False, None) == 'Nouvelle inapplicabilité'
    assert _title(AMOperation.ADD_WARNING, False, None) == 'Nouvel avertissement'

    assert _title(AMOperation.ADD_ALTERNATIVE_SECTION, True, '1') == 'Section alternative #1'
    assert _title(AMOperation.ADD_CONDITION, True, '1') == 'Inapplicabilité #1'
    assert _title(AMOperation.ADD_WARNING, True, '1') == 'Avertissement #1'
