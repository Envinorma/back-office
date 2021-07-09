import traceback
from typing import Any, Dict

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash import Dash
from dash.dependencies import MATCH, Input, Output, State
from dash.development.base_component import Component

from back_office.utils import generate_id

from .common_ids import AM_ID, extract_id_type_and_key_from_context
from .handlers import SaveError, edit_am_title


def _edit_title_id(section_id: Any) -> Dict[str, Any]:
    return {'type': generate_id(__file__, 'edit-title'), 'key': section_id}


def _form_id(section_id: Any) -> Dict[str, Any]:
    return {'type': generate_id(__file__, 'form'), 'key': section_id}


def _form_output_id(section_id: Any) -> Dict[str, Any]:
    return {'type': generate_id(__file__, 'form-output'), 'key': section_id}


def _form_wrapper_id(section_id: Any) -> Dict[str, Any]:
    return {'type': generate_id(__file__, 'form-wrapper'), 'key': section_id}


def _title_value_id(section_id: Any) -> Dict[str, Any]:
    return {'type': generate_id(__file__, 'title-value'), 'key': section_id}


def _submit_edition_id(section_id: Any) -> Dict[str, Any]:
    return {'type': generate_id(__file__, 'submit-edition'), 'key': section_id}


def _cancel_edition_id(section_id: Any) -> Dict[str, Any]:
    return {'type': generate_id(__file__, 'cancel-edition'), 'key': section_id}


def _title_value(title: str, section_id: str) -> Component:
    content = title if title else html.Div('Aucun titre', className='text-muted')
    return html.Strong(content, id=_title_value_id(section_id))


def _form(title: str, section_id: str) -> Component:
    return html.Div(
        [
            dcc.Textarea(value=title, id=_form_id(section_id), className='form-control'),
            html.Div(id=_form_output_id(section_id)),
            html.Button('Valider', id=_submit_edition_id(section_id), className='btn btn-success mt-2'),
            html.Button('Annuler', id=_cancel_edition_id(section_id), className='btn btn-danger mt-2 ml-2'),
        ],
        id=_form_wrapper_id(section_id),
        hidden=True,
    )


def editable_title(title: str, section_id: str) -> Component:
    return html.Div(
        [
            html.Div(_title_value(title, section_id), className='editable-title p-2', id=_edit_title_id(section_id)),
            _form(title, section_id),
        ]
    )


def editable_title_callbacks(app: Dash) -> None:
    @app.callback(
        Output(_form_wrapper_id(MATCH), 'hidden'),
        Output(_edit_title_id(MATCH), 'hidden'),
        Output(_form_output_id(MATCH), 'children'),
        Output(_title_value_id(MATCH), 'children'),
        Input(_edit_title_id(MATCH), 'n_clicks'),
        Input(_cancel_edition_id(MATCH), 'n_clicks'),
        Input(_submit_edition_id(MATCH), 'n_clicks'),
        State(_form_id(MATCH), 'value'),
        State(AM_ID, 'data'),
        prevent_initial_call=True,
    )
    def _handle_edit_title(click_1, click_2, click_3, new_content, am_id):
        type_, section_id = extract_id_type_and_key_from_context()
        if type_ == _edit_title_id('')['type']:
            return False, True, html.Div(), dash.no_update
        if type_ == _submit_edition_id('')['type']:
            try:
                edit_am_title(am_id, section_id, new_content)
            except SaveError as exc:
                return False, True, dbc.Alert(str(exc), className='mt-2', color='danger'), new_content
            except Exception:  # pylint: disable=broad-except
                error_alert = dbc.Alert(f'Erreur inconnue {traceback.format_exc()}', className='mt-2', color='danger')
                return (False, True, error_alert, new_content)
            return True, False, html.Div(), new_content
        return True, False, html.Div(), dash.no_update
