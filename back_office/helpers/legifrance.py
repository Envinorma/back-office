import random
from datetime import date, datetime
from typing import Optional

from envinorma.from_legifrance.legifrance_to_am import legifrance_to_arrete_ministeriel
from envinorma.models import ArreteMinisteriel
from leginorma import LegifranceClient, LegifranceRequestError, LegifranceText

from back_office.config import LEGIFRANCE_CLIENT_ID, LEGIFRANCE_CLIENT_SECRET

LEGIFRANCE_CLIENT = None
NO_CONSOLIDATION_ERROR_MESSAGE = "L'expression à valider est fausse."


class NoConsolidationError(Exception):
    pass


def get_legifrance_client() -> LegifranceClient:
    global LEGIFRANCE_CLIENT
    if not LEGIFRANCE_CLIENT:
        LEGIFRANCE_CLIENT = LegifranceClient(LEGIFRANCE_CLIENT_ID, LEGIFRANCE_CLIENT_SECRET)
    return LEGIFRANCE_CLIENT


def _to_datetime(date_: date) -> datetime:
    return datetime(date_.year, date_.month, date_.day)


def _is_a_missing_consolidation_error(error: LegifranceRequestError) -> bool:
    return NO_CONSOLIDATION_ERROR_MESSAGE in str(error)


def _fetch_legifrance_text(am_id: str, datetime_: datetime, fallback_to_non_consolidated: bool) -> LegifranceText:
    try:
        response = get_legifrance_client().consult_law_decree(am_id, datetime_)
    except LegifranceRequestError as exc:
        if not _is_a_missing_consolidation_error(exc):
            raise
        if not fallback_to_non_consolidated:
            raise NoConsolidationError
        response = get_legifrance_client().consult_jorf(am_id)
    return LegifranceText.from_dict(response)


def extract_legifrance_am(
    am_id: str, date_: Optional[date] = None, fallback_to_non_consolidated: bool = False
) -> ArreteMinisteriel:
    """Extracts legifrance arrete_ministeriel from id and date. If date is None,
    it will be set to today. If fallback_to_non_consolidated is True,
    it will try to extract from the non-consolidated version of the arrete_ministeriel if
    the consolidated version is not available.

    Args:
        am_id (str): the id of the arrete_ministeriel
        date_ (Optional[date], optional): the date of the version to be extracted. Defaults to today.
        fallback_to_non_consolidated (bool, optional): if True, it will try to extract from
            the non-consolidated version of the arrete_ministeriel if the consolidated version is not available.
            Defaults to False.

    Returns:
        ArreteMinisteriel: the arrete_ministeriel extracted from legifrance
    """
    datetime_ = _to_datetime(date_ or date.today())
    legifrance_current_version = _fetch_legifrance_text(am_id, datetime_, fallback_to_non_consolidated)
    random.seed(legifrance_current_version.title)
    return legifrance_to_arrete_ministeriel(legifrance_current_version, am_id=am_id)
