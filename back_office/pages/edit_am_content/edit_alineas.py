import traceback
from typing import Any, Dict, List

import dash
import dash_bootstrap_components as dbc
from dash import MATCH, Dash, Input, Output, State, dcc, html
from dash.development.base_component import Component
from envinorma.models import EnrichedString

from back_office.components.am_component import table_to_component
from back_office.pages.edit_am_content.handlers import SaveError, edit_am_alineas
from back_office.utils import generate_id

from .alinea_converters import alineas_to_textarea_value, textarea_value_to_alineas
from .common_ids import AM_ID, extract_id_type_and_key_from_context


def _edit_alineas_id(section_id: Any) -> Dict[str, Any]:
    return {'type': generate_id(__file__, 'edit-alineas'), 'key': section_id}


def _form_id(section_id: Any) -> Dict[str, Any]:
    return {'type': generate_id(__file__, 'form'), 'key': section_id}


def _form_output_id(section_id: Any) -> Dict[str, Any]:
    return {'type': generate_id(__file__, 'form-output'), 'key': section_id}


def _form_wrapper_id(section_id: Any) -> Dict[str, Any]:
    return {'type': generate_id(__file__, 'form-wrapper'), 'key': section_id}


def _alineas_value_id(section_id: Any) -> Dict[str, Any]:
    return {'type': generate_id(__file__, 'alineas-value'), 'key': section_id}


def _submit_edition_id(section_id: Any) -> Dict[str, Any]:
    return {'type': generate_id(__file__, 'submit-edition'), 'key': section_id}


def _cancel_edition_id(section_id: Any) -> Dict[str, Any]:
    return {'type': generate_id(__file__, 'cancel-edition'), 'key': section_id}


def _alinea(alinea: EnrichedString) -> Component:
    if alinea.table:
        return table_to_component(alinea.table, None)
    return html.Div(alinea.text)


def _alineas(alineas: List[EnrichedString]) -> Component:
    children = [_alinea(alinea) for alinea in alineas] if alineas else html.Div('Aucun alineas', className='text-muted')
    return html.Div(children)


def _alineas_wrapper(alineas: List[EnrichedString], section_id: str) -> Component:
    return html.Div(_alineas(alineas), _alineas_value_id(section_id))


def _text_area(alineas: List[EnrichedString], section_id: str) -> Component:
    return dcc.Textarea(
        value=alineas_to_textarea_value(alineas),
        id=_form_id(section_id),
        className='form-control',
        style={'height': f'{len(alineas) * 50 + 50}px'},
    )


def _form(alineas: List[EnrichedString], section_id: str) -> Component:
    return html.Div(
        [
            _text_area(alineas, section_id),
            html.Div(id=_form_output_id(section_id)),
            html.Button('Valider', id=_submit_edition_id(section_id), className='btn btn-success mt-2'),
            html.Button('Annuler', id=_cancel_edition_id(section_id), className='btn btn-danger mt-2 ml-2'),
        ],
        id=_form_wrapper_id(section_id),
        hidden=True,
    )


def editable_alineas(alineas: List[EnrichedString], section_id: str) -> Component:
    return html.Div(
        [
            html.Div(
                _alineas_wrapper(alineas, section_id), className='editable-alineas p-2', id=_edit_alineas_id(section_id)
            ),
            _form(alineas, section_id),
        ]
    )


def editable_alineas_callbacks(app: Dash) -> None:
    @app.callback(
        Output(_form_wrapper_id(MATCH), 'hidden'),
        Output(_edit_alineas_id(MATCH), 'hidden'),
        Output(_form_output_id(MATCH), 'children'),
        Output(_alineas_value_id(MATCH), 'children'),
        Input(_edit_alineas_id(MATCH), 'n_clicks'),
        Input(_cancel_edition_id(MATCH), 'n_clicks'),
        Input(_submit_edition_id(MATCH), 'n_clicks'),
        State(_form_id(MATCH), 'value'),
        State(AM_ID, 'data'),
        prevent_initial_call=True,
    )
    def _handle_edit_alineas(click_1, click_2, click_3, new_content, am_id):
        type_, section_id = extract_id_type_and_key_from_context()
        if type_ == _edit_alineas_id('')['type']:
            return False, True, html.Div(), dash.no_update
        if type_ == _submit_edition_id('')['type']:
            try:
                new_alineas = textarea_value_to_alineas(new_content)
                edit_am_alineas(am_id, section_id, new_alineas)
                return True, False, html.Div(), _alineas(new_alineas)
            except SaveError as exc:
                return False, True, dbc.Alert(str(exc), className='mt-2', color='danger'), html.Div()
            except Exception:  # pylint: disable=broad-except
                error_alert = dbc.Alert(f'Erreur inconnue {traceback.format_exc()}', className='mt-2', color='danger')
                return (False, True, error_alert, html.Div())
        return True, False, html.Div(), dash.no_update
