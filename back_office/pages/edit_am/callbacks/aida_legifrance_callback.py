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
        Output(ids.TEXT_AREA_COMPONENT, 'value'),
        Output(ids.AIDA_OUTPUT, 'children'),
        Output(ids.TEXT_AREA_COMPONENT, 'children'),
        Input(ids.FETCH_AIDA, 'n_clicks'),
        Input(ids.FETCH_LEGIFRANCE, 'n_clicks'),
        State(ids.AM_ID, 'data'),
        prevent_initial_call=True,
    )
    def _edit_am(_, __, am_id: str) -> Tuple[str, Component, List[Component]]:
        try:
            from_legifrance = ids.FETCH_LEGIFRANCE in dash.callback_context.triggered[0]['prop_id']
            metadata = DATA_FETCHER.load_am_metadata(am_id)
            if not metadata:
                raise ValueError('AM Metadata not found.')
            success = success_component('Texte AIDA récupéré avec succès')
            return '', success, _parse(metadata.aida_page, am_id, from_legifrance)
        except _FrenchError as exc:
            error_message = str(exc)
        except Exception:  # pylint: disable=broad-except
            error_message = f'Erreur inattendue: \n{traceback.format_exc()}'
        return '', error_component(error_message), cast(list, dash.no_update)
