from typing import Any, Callable, Dict, List, Optional

import dash
import dash_bootstrap_components as dbc
import dash_html_components as html
from dash.dependencies import MATCH, Input, Output, State
from dash.development.base_component import Component
from envinorma.data import ArreteMinisteriel

from back_office.components.parametric_am import parametric_am_callbacks, parametric_am_component
from back_office.components.table import ExtendedComponent, table_component


def _close_modal_button_id(page_id: str, key: Optional[str]) -> Dict[str, Any]:
    return {'type': f'{page_id}-param-am-close-modal-button', 'key': key or MATCH}


def _modal_id(page_id: str, key: Optional[str]) -> Dict[str, Any]:
    return {'type': f'{page_id}-param-am-modal', 'key': key or MATCH}


def _modal_trigger_id(page_id: str, key: Optional[str]) -> Dict[str, Any]:
    return {'type': f'{page_id}-param-am-modal-trigger', 'key': key or MATCH}


_AMModalGenerator = Callable[[str, ArreteMinisteriel], Component]


def _get_am_modal_generator(page_id: str) -> _AMModalGenerator:
    def _am_modal(filename: str, am: ArreteMinisteriel) -> Component:
        modal = dbc.Modal(
            [
                dbc.ModalHeader(filename),
                dbc.ModalBody(parametric_am_component(am, page_id)),
                dbc.ModalFooter(
                    [html.Button('Fermer', id=_close_modal_button_id(page_id, filename), className='btn btn-light')]
                ),
            ],
            size='xl',
            id=_modal_id(page_id, filename),
            scrollable=True,
        )
        link = html.Button(filename, id=_modal_trigger_id(page_id, filename), className='btn btn-link')
        return html.Span([link, modal])

    return _am_modal


def _generate_am_row(am: ArreteMinisteriel, _am_modal_generator: _AMModalGenerator) -> List[ExtendedComponent]:
    link = _am_modal_generator('Consulter', am)
    if not am.version:
        raise ValueError('Expecting non null version descriptor.')
    aed_left_date = str(am.version.aed_date_parameter.left_date) or ''
    aed_right_date = str(am.version.aed_date_parameter.right_date) or ''
    installation_left_date = str(am.version.installation_date_parameter.left_date) or ''
    installation_right_date = str(am.version.installation_date_parameter.right_date) or ''
    return [link, am.id or '', aed_left_date, aed_right_date, installation_left_date, installation_right_date]


def _generate_am_table(
    filename_to_am: Dict[str, ArreteMinisteriel], _am_modal_generator: _AMModalGenerator
) -> Component:
    header = [
        f'{len(filename_to_am)} versions',
        'CID',
        'Date d\'AED postérieure à',
        'Date d\'AED antérieure à',
        'Date d\'installation postérieure à',
        'Date d\'installation antérieure à',
    ]
    rows = [_generate_am_row(am, _am_modal_generator) for _, am in sorted(filename_to_am.items())]
    return table_component([header], rows)


def parametric_am_list_callbacks(app: dash.Dash, page_id: str) -> None:
    @app.callback(
        Output(_modal_id(page_id, None), 'is_open'),
        Input(_modal_trigger_id(page_id, None), 'n_clicks'),
        Input(_close_modal_button_id(page_id, None), 'n_clicks'),
        State(_modal_id(page_id, None), 'is_open'),
        prevent_initial_call=True,
    )
    def _toggle_modal(n_clicks, n_clicks_2, is_open):
        if n_clicks or n_clicks_2:
            return not is_open
        return False

    parametric_am_callbacks(app, page_id)


def parametric_am_list_component(name_to_am: Dict[str, ArreteMinisteriel], page_id: str) -> Component:
    return _generate_am_table(name_to_am, _get_am_modal_generator(page_id))
