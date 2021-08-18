from datetime import date

import pytest
from envinorma.models import AMMetadata, AMSource, AMState, Classement, Regime

from back_office.pages.create_am.am_creation_form_handling import FormHandlingError, _extract_am_metadata


def test_extract_am_metadata():
    expected = AMMetadata(
        aida_page='5619',
        title='Arrêté du 01/02/21 relatif aux...',
        nor='DEVP0123456A',
        classements=[Classement(regime=Regime('E'), rubrique='5000', alinea='A.2')],
        cid='JORFTEXT000012345678',
        state=AMState('VIGUEUR'),
        date_of_signature=date.fromisoformat('2021-02-01'),
        source=AMSource('LEGIFRANCE'),
        is_transverse=True,
        nickname='GF',
    )
    args = {
        'am_id': 'JORFTEXT000012345678',
        'title': 'Arrêté du 01/02/21 relatif aux...',
        'aida_page': '5619',
        'am_state': 'VIGUEUR',
        'am_source': 'LEGIFRANCE',
        'nor_id': 'DEVP0123456A',
        'reason_deleted': None,
        'rubriques': ['5000'],
        'regimes': ['E'],
        'alineas': ['A.2'],
        'is_transverse': True,
        'nickname': 'GF',
    }
    assert _extract_am_metadata(**args) == expected

    with pytest.raises(FormHandlingError):
        _extract_am_metadata(**{**args, 'am_id': 'JORFTEXT000012345'})

    with pytest.raises(FormHandlingError):
        _extract_am_metadata(**{**args, 'title': 'Arrêté du 01/02/21...'})
    with pytest.raises(FormHandlingError):
        _extract_am_metadata(**{**args, 'title': 'Arrêté du 01/02/2021 relatif à...'})

    with pytest.raises(FormHandlingError):
        _extract_am_metadata(**{**args, 'aida_page': ''})
    with pytest.raises(FormHandlingError):
        _extract_am_metadata(**{**args, 'aida_page': '1234a'})
    with pytest.raises(FormHandlingError):
        _extract_am_metadata(**{**args, 'aida_page': '01234a'})
    _extract_am_metadata(**{**args, 'aida_page': '01234'})

    with pytest.raises(FormHandlingError):
        _extract_am_metadata(**{**args, 'am_state': None})
    with pytest.raises(FormHandlingError):
        _extract_am_metadata(**{**args, 'am_state': 'TEST'})
    _extract_am_metadata(**{**args, 'am_state': 'ABROGE'})
    _extract_am_metadata(**{**args, 'am_state': 'VIGUEUR'})

    with pytest.raises(FormHandlingError):
        _extract_am_metadata(**{**args, 'am_source': None})

    with pytest.raises(FormHandlingError):
        _extract_am_metadata(**{**args, 'nor_id': None})
    with pytest.raises(FormHandlingError):
        _extract_am_metadata(**{**args, 'nor_id': 'TOO_SHORT'})

    with pytest.raises(FormHandlingError):
        _extract_am_metadata(**{**args, 'reason_deleted': 'should be empty'})
    with pytest.raises(FormHandlingError):
        _extract_am_metadata(**{**args, 'reason_deleted': '', 'am_state': 'DELETED'})

    with pytest.raises(FormHandlingError):
        _extract_am_metadata(**{**args, 'rubriques': ['']})
    with pytest.raises(FormHandlingError):
        _extract_am_metadata(**{**args, 'rubriques': ['rubrique']})

    with pytest.raises(FormHandlingError):
        _extract_am_metadata(**{**args, 'regimes': ['']})
    with pytest.raises(FormHandlingError):
        _extract_am_metadata(**{**args, 'regimes': [None]})
    with pytest.raises(FormHandlingError):
        _extract_am_metadata(**{**args, 'regimes': ['alpha']})
