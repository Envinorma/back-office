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

    assert _title(AMOperation.ADD_ALTERNATIVE_SECTION, False, None) == 'Nouveau paragraphe alternatif'
    assert _title(AMOperation.ADD_CONDITION, False, None) == 'Nouvelle condition de non-application'
    assert _title(AMOperation.ADD_WARNING, False, None) == 'Nouvel avertissement'

    assert _title(AMOperation.ADD_ALTERNATIVE_SECTION, True, '1') == 'Paragraphe alternatif #1'
    assert _title(AMOperation.ADD_CONDITION, True, '1') == 'Condition de non-application #1'
    assert _title(AMOperation.ADD_WARNING, True, '1') == 'Avertissement #1'
