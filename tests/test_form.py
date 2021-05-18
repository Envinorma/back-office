from back_office.pages.parametrization_edition.form import _title
from back_office.utils import AMOperation


def test_title():
    # Test all operations are handled
    for operation in AMOperation:
        try:
            _title(operation, True, 1)
            _title(operation, False, -1)
        except ValueError:
            pass  # This exception occurs for some operations

    assert _title(AMOperation.ADD_ALTERNATIVE_SECTION, False, -1) == 'Nouveau paragraphe alternatif'
    assert _title(AMOperation.ADD_CONDITION, False, -1) == 'Nouvelle condition de non-application'
    assert _title(AMOperation.ADD_WARNING, False, -1) == 'Nouvel avertissement'

    assert _title(AMOperation.ADD_ALTERNATIVE_SECTION, True, 1) == 'Paragraphe alternatif n°1'
    assert _title(AMOperation.ADD_CONDITION, True, 1) == 'Condition de non-application n°1'
    assert _title(AMOperation.ADD_WARNING, True, 1) == 'Avertissement n°1'
