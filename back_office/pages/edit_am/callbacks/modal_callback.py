from typing import List, Optional

from dash import Dash, Input, Output, State
from dash.development.base_component import Component
from envinorma.models.arrete_ministeriel import ArreteMinisteriel
from envinorma.models.text_elements import EnrichedString
from text_diff import text_differences

from back_office.components.diff import diff_component
from back_office.helpers.diff import extract_am_lines
from back_office.utils import DATA_FETCHER

from .. import ids
from .save_callback import extract_text_from_html


def _previous_lines(am_id: str) -> List[str]:
    previous_am = DATA_FETCHER.load_most_advanced_am(am_id)
    if not previous_am:
        return []
    return extract_am_lines(previous_am, False)


def _new_lines(am_id: str, form_am_value: Optional[str]) -> List[str]:
    if not form_am_value:
        return []
    sections = extract_text_from_html(form_am_value)
    am = ArreteMinisteriel(id=am_id, title=EnrichedString('Faux arrêté'), visa=[], sections=sections)
    return extract_am_lines(am, False)


def _diff(am_id: str, form_am_value: Optional[str]) -> Component:
    previous_lines = _previous_lines(am_id)
    new_lines = _new_lines(am_id, form_am_value)
    diff = text_differences(previous_lines, new_lines)
    return diff_component(diff, 'Version précédente', 'Nouvelle version')


def add_callbacks(app: Dash) -> None:
    @app.callback(
        Output(ids.MODAL, 'is_open'),
        Input(ids.DIFF_BUTTON, 'n_clicks'),
        Input(ids.SAVE_BUTTON, 'n_clicks'),
        State(ids.MODAL, 'is_open'),
        prevent_initial_call=True,
    )
    def _toggle_modal(n_clicks, n_clicks_submit, is_open):
        if n_clicks or n_clicks_submit:
            return not is_open
        return False

    @app.callback(
        Output(ids.DIFF, 'children'),
        Input(ids.DIFF_BUTTON, 'n_clicks'),
        State(ids.AM_ID, 'data'),
        State(ids.TEXT_AREA_COMPONENT, 'value'),
        prevent_initial_call=True,
    )
    def _build_diff(_, am_id, form_am_value):
        return _diff(am_id, form_am_value)
