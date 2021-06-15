from pathlib import Path

from envinorma.models.text_elements import Table, Title

from back_office.pages.edit_am.am_init_edition import _extract_elements, _extract_structured_text


def test_extract_elements():
    assert _extract_elements('') == []
    assert _extract_elements('\n') == []
    res = _extract_elements('\n<table><tr><td></td></tr></table>')
    assert len(res) == 1
    assert isinstance(res[0], Table)

    res = _extract_elements('Test\n<table><tr><td></td></tr></table>')
    assert len(res) == 2
    assert res[0] == 'Test'
    assert isinstance(res[1], Table)

    res = _extract_elements('Test\nTest')
    assert len(res) == 2
    assert res[0] == 'Test'
    assert res[1] == 'Test'

    res = _extract_elements('Test\nTest\n#Test')
    assert len(res) == 3
    assert res[0] == 'Test'
    assert res[1] == 'Test'
    title = res[2]
    assert isinstance(title, Title)
    assert title.text == 'Test'
    assert title.level == 1


def test_extract_structured_text():
    am_str = open(Path(__file__).parent / 'data' / 'arrete_ministeriel.txt').read()
    text = _extract_structured_text(am_str)
    assert text.title.text == ''
    assert len(text.sections) == 4
    assert text.sections[0].title.text == 'Article 1 er'
    assert text.outer_alineas == []
