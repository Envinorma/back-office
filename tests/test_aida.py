from back_office.helpers.aida import extract_anchors, extract_hyperlinks


def test_hyperlinks_extraction():
    input_ = '<div id="content-area"><a href="A">PipA</a> Bonjour <a href="B">PipB</a> <a>No HREF here</a></div>'
    tags = extract_hyperlinks(input_)
    assert len(tags) == 2
    assert any([tag.href == 'A' for tag in tags])
    assert any([tag.href == 'B' for tag in tags])
    assert any([tag.content == 'PipA' for tag in tags])


def test_extract_anchors():
    html = '''
        <div id="content-area">
            <h1>Bonjour</h1>

            <p><a name="nope"></a>Je m'appelle Pipa.</p>

            <h2><a name="et-toi"></a>Et toi ?</h2>

            <h3><a href="example.com">Bye.</a></h3>
        </div>
    '''
    anchors = extract_anchors(html)
    assert len(anchors) == 1
    assert anchors[0].anchored_text == 'Et toi ?'
    assert anchors[0].name == 'et-toi'
