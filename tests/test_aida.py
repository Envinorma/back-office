from back_office.helpers.aida import _truncate_title


def test_truncate_title():
    title = 'A title that should not be truncated'
    truncated_title = _truncate_title(title)
    assert truncated_title == title

    title = "Article 1er de l'arrêté du 28 juin 2013"
    truncated_title = _truncate_title(title)
    assert truncated_title == 'Article 1er'
