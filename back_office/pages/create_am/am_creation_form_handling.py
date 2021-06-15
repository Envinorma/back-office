from datetime import date
from typing import List, Optional

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.development.base_component import Component
from envinorma.models import (
    DELETE_REASON_MIN_NB_CHARS,
    AMMetadata,
    AMSource,
    AMState,
    Classement,
    Regime,
    extract_date_of_signature,
)

from back_office.pages.parametrization_edition.form_handling import FormHandlingError
from back_office.utils import DATA_FETCHER

from . import create_am_ids as page_ids


def is_legifrance_id_valid(legifrance_id: str) -> bool:
    return len(legifrance_id) == 20 or 'FAKE' in legifrance_id


def _build_cid(am_id: Optional[str]) -> str:
    if am_id is None:
        raise FormHandlingError('L\'id Légifrance doit être défini.')
    if not is_legifrance_id_valid(am_id):
        raise FormHandlingError('L\'id Légifrance doit contenir 20 caractères.')
    return am_id


def _build_aida_page(aida_page: Optional[str]) -> str:
    if not aida_page:
        raise FormHandlingError('La page AIDA doit être renseignée.')
    if any([not x.isdigit() for x in aida_page]):
        raise FormHandlingError('La page AIDA doit être consitituée de chiffres uniquement.')
    return aida_page


def _extract_title_date(title: Optional[str]) -> date:
    try:
        return extract_date_of_signature(title or '')
    except ValueError:
        raise FormHandlingError(
            'Mauvais format de titre. Format attendu : "Arrêté du jj/mm/yy '
            'relatif..." ou "Arrêté du jj/mm/yy fixant..."'
        )


def _build_title(title: Optional[str]) -> str:
    _extract_title_date(title)  # To check title format
    return title or ''


def _ensure_rubrique(candidate: str) -> str:
    if len(candidate) != 4 or candidate[0] not in '12345':
        raise FormHandlingError('Rubrique invalide. Format attendu : 1XXX, 2XXX, 3XXX ou 4XXX')
    try:
        int(candidate)
    except FormHandlingError:
        raise FormHandlingError('Rubrique invalide. Format attendu : 1XXX, 2XXX, 3XXX ou 4XXX')
    return candidate


def _build_rubrique(rubrique: Optional[str]) -> str:
    if not rubrique:
        raise FormHandlingError('La rubrique doit être renseignée.')
    return _ensure_rubrique(rubrique)


def _build_regime(regime: Optional[str]) -> Regime:
    if not regime:
        raise FormHandlingError('Le régime doit être renseigné.')
    try:
        return Regime(regime)
    except ValueError:
        raise FormHandlingError('Régime invalide.')


def _build_classement(rubrique: Optional[str], regime: Optional[str], alinea: Optional[str]) -> Classement:
    return Classement(_build_rubrique(rubrique), _build_regime(regime), alinea)


def _build_classements(
    rubriques: List[Optional[str]], regimes: List[Optional[str]], alineas: List[Optional[str]]
) -> List[Classement]:
    if len(rubriques) != len(regimes) or len(regimes) != len(alineas):
        raise ValueError(f'Expecting lists of same lengths, got {len(rubriques)}, {len(regimes)} and {len(alineas)}.')
    return [
        _build_classement(rubrique, regime, alinea) for rubrique, regime, alinea in zip(rubriques, regimes, alineas)
    ]


def _build_state(am_state: Optional[str]) -> AMState:
    if not am_state:
        raise FormHandlingError('Le statut de l\'AM doit être renseigné.')
    try:
        return AMState(am_state)
    except ValueError:
        raise FormHandlingError('Le statut de l\'AM est invalide.')


def _build_date_of_signature(title: Optional[str]) -> date:
    return _extract_title_date(title)


def _build_source(am_source: Optional[str]) -> AMSource:
    if not am_source:
        raise FormHandlingError('La source de l\'AM doit être renseigné.')
    try:
        return AMSource(am_source)
    except ValueError:
        raise FormHandlingError('La source de l\'AM est invalide.')


def _build_nor(nor_id: Optional[str]) -> str:
    if nor_id is None:
        raise FormHandlingError('Le numéro NOR doit être défini.')
    if len(nor_id) != 12:
        raise FormHandlingError('Le numéro NOR doit contenir 12 caractères.')
    return nor_id


def _build_reason_deleted(am_state: Optional[str], reason_deleted: Optional[str]) -> Optional[str]:
    state = _build_state(am_state)
    if state == AMState.DELETED and len(reason_deleted or '') < DELETE_REASON_MIN_NB_CHARS:
        raise FormHandlingError(
            f'La raison de suppression doit contenir au moins {DELETE_REASON_MIN_NB_CHARS} caractères.'
        )
    if state != AMState.DELETED and reason_deleted:
        raise FormHandlingError(
            'La raison de suppression ne doit être renseignée que si le statut choisi est différent de DELETED.'
        )
    return reason_deleted


def _extract_am_metadata(
    am_id: Optional[str],
    title: Optional[str],
    aida_page: Optional[str],
    am_state: Optional[str],
    am_source: Optional[str],
    nor_id: Optional[str],
    reason_deleted: Optional[str],
    rubriques: List[Optional[str]],
    regimes: List[Optional[str]],
    alineas: List[Optional[str]],
) -> AMMetadata:
    return AMMetadata(
        _build_cid(am_id),
        _build_aida_page(aida_page),
        _build_title(title),
        _build_classements(rubriques, regimes, alineas),
        _build_state(am_state),
        _build_date_of_signature(title),
        _build_source(am_source),
        _build_nor(nor_id),
        _build_reason_deleted(am_state, reason_deleted),
    )


def handle_form(
    am_id: Optional[str],
    title: Optional[str],
    aida_page: Optional[str],
    am_state: Optional[str],
    am_source: Optional[str],
    nor_id: Optional[str],
    reason_deleted: Optional[str],
    rubriques: List[Optional[str]],
    regimes: List[Optional[str]],
    alineas: List[Optional[str]],
) -> Component:
    try:
        new_am_metadata = _extract_am_metadata(
            am_id,
            title,
            aida_page,
            am_state,
            am_source,
            nor_id,
            reason_deleted,
            rubriques,
            regimes,
            alineas,
        )
        DATA_FETCHER.upsert_am(new_am_metadata)
    except FormHandlingError as exc:
        return dbc.Alert(f'Erreur dans le formulaire :\n{exc}', color='danger')
    except Exception as exc:
        return dbc.Alert(f'Erreur inattendue :\n{exc}', color='danger')
    return html.Div(
        [dbc.Alert('Enregistrement réussi.', color='success'), dcc.Location(href='/', id=page_ids.SUCCESS_REDIRECT)]
    )
