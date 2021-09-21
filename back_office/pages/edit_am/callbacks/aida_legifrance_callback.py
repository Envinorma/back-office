import traceback
from typing import List, Tuple, cast

import dash
from dash import Input, Output, State
from dash.development.base_component import Component
from envinorma.models import ArreteMinisteriel

from back_office.components import error_component, success_component
from back_office.helpers.aida import extract_aida_am
from back_office.helpers.legifrance import NoConsolidationError, extract_legifrance_am
from back_office.utils import DATA_FETCHER

from .. import ids
from ..components.text_area_am import text_area_value


class _FrenchError(Exception):
    pass


def _parse_legifrance(am_id: str) -> ArreteMinisteriel:
    try:
        return extract_legifrance_am(am_id)
    except NoConsolidationError:
        raise _FrenchError('L\'AM Légifrance n\'existe pas en version consolidée et ne peut donc pas être utilisé.')


def _parse(aida_id: str, am_id: str, from_legifrance: bool) -> List[Component]:
    if from_legifrance:
        am = _parse_legifrance(am_id)
    else:
        am = extract_aida_am(aida_id, am_id)
    if not am:
        raise _FrenchError('Aucun AM trouvé sur cette page.')
    return text_area_value(am)


def add_callbacks(app: dash.Dash) -> None:
    @app.callback(
        Output(ids.HIDDEN_BUTTON, 'n_clicks'),
        Output(ids.AIDA_LEGIFRANCE_OUTPUT, 'children'),
        Output(ids.TEXT_AREA_COMPONENT, 'children'),
        Input(ids.AIDA_LEGIFRANCE_CONFIRM, 'n_clicks'),
        State(ids.FROM_LEGIFRANCE_OR_AIDA, 'data'),
        State(ids.AM_ID, 'data'),
        prevent_initial_call=True,
    )
    def confirm(_, from_aida_or_legifrance: str, am_id: str) -> Tuple[int, Component, List[Component]]:
        try:
            if from_aida_or_legifrance == 'aida':
                from_legifrance = False
            elif from_aida_or_legifrance == 'legifrance':
                from_legifrance = True
            else:
                raise ValueError(f'Unknown value for "from_aida_or_legifrance": {from_aida_or_legifrance}')
            metadata = DATA_FETCHER.load_am_metadata(am_id)
            if not metadata:
                raise ValueError('AM Metadata not found.')
            source = 'Legifrance' if from_legifrance else 'AIDA'
            success = success_component(f'Texte {source} récupéré avec succès')
            return 1, success, _parse(metadata.aida_page, am_id, from_legifrance)
        except _FrenchError as exc:
            error_message = str(exc)
        except Exception:  # pylint: disable=broad-except
            error_message = f'Erreur inattendue: \n{traceback.format_exc()}'
        return 1, error_component(error_message), cast(list, dash.no_update)

    @app.callback(
        Output(ids.FROM_LEGIFRANCE_OR_AIDA, 'data'),
        Input(ids.FETCH_AIDA, 'n_clicks'),
        Input(ids.FETCH_LEGIFRANCE, 'n_clicks'),
        prevent_initial_call=True,
    )
    def _edit_am(_, __) -> str:
        from_legifrance = ids.FETCH_LEGIFRANCE in dash.callback_context.triggered[0]['prop_id']
        if from_legifrance:
            return 'legifrance'
        return 'aida'

    @app.callback(
        Output(ids.AIDA_LEGIFRANCE_MODAL, 'is_open'),
        Input(ids.FETCH_AIDA, 'n_clicks'),
        Input(ids.FETCH_LEGIFRANCE, 'n_clicks'),
        Input(ids.AIDA_LEGIFRANCE_CONFIRM, 'n_clicks'),
        State(ids.AIDA_LEGIFRANCE_MODAL, 'is_open'),
        prevent_initial_call=True,
    )
    def _toggle_modal(_, __, ___, is_open):
        return not is_open
