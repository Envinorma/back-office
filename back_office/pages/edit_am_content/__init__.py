from typing import Any, Dict, Optional

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash import Dash
from dash.dependencies import ALL, Input, Output, State
from dash.development.base_component import Component
from envinorma.models import ArreteMinisteriel, StructuredText

from back_office.routing import Endpoint, Page
from back_office.utils import DATA_FETCHER, generate_id

from .common_ids import AM_ID, extract_id_type_and_key_from_context
from .edit_alineas import editable_alineas, editable_alineas_callbacks
from .edit_title import editable_title, editable_title_callbacks
from .handlers import delete_am_section, insert_empty_section

_LAYOUT = generate_id(__file__, 'layout')
_BUTTONS_HIDDEN = generate_id(__file__, 'buttons-hidden')


def _delete_section_id(section_id) -> Dict[str, Any]:
    return {'type': generate_id(__file__, 'delete-section'), 'key': section_id}


def _add_section_id(section_id) -> Dict[str, Any]:
    return {'type': generate_id(__file__, 'add-section'), 'key': section_id}


def _toggler(am_id: str) -> Component:
    return dcc.Link(
        html.Button('Activer la modification la structure', className='btn btn-secondary btn-sm mb-2'),
        href=f'/{Endpoint.EDIT_AM_CONTENT}/{am_id}/with_buttons',
    )


def _title(am_id: str) -> Component:
    return html.H3(f"Edition de l'arrêté {am_id}")


def _delete_section_button(section_id: str, hidden: bool) -> Component:
    return html.Button(
        'supprimer la section',
        className='btn btn-link btn-sm text-danger pl-2',
        id=_delete_section_id(section_id),
        hidden=hidden,
    )


def _add_section_button(section_id: str, hidden: bool) -> Component:
    return html.Div(
        html.Button(
            '+ nouvelle section', className='btn btn-link btn-sm', id=_add_section_id(section_id), hidden=hidden
        ),
        className='pl-4',
        style={'border-left': '3px solid #007bff'},
    )


def _section(section: StructuredText, buttons_hidden: bool) -> Component:
    return html.Div(
        [
            editable_title(section.title.text, section.id),
            _delete_section_button(section.id, buttons_hidden),
            editable_alineas(section.outer_alineas, section.id),
            *[_section(sub, buttons_hidden) for sub in section.sections],
            _add_section_button(section.id, buttons_hidden),
        ],
        className='pl-4',
        style={'border-left': '3px solid #007bff'},
    )


def _am(am: ArreteMinisteriel, buttons_hidden: bool) -> Component:
    return html.Div([_section(section, buttons_hidden) for section in am.sections])


def _am_id(am_id: str) -> Component:
    return dcc.Store(id=AM_ID, data=am_id)


def _buttons_hidden(buttons_hidden: bool) -> Component:
    return dcc.Store(id=_BUTTONS_HIDDEN, data=buttons_hidden)


def _layout_if_logged(am_id: str, buttons_hidden: bool = True) -> Component:
    am = DATA_FETCHER.load_most_advanced_am(am_id)
    if not am:
        return html.Div('AM introuvable.')

    return html.Div(
        [
            _title(am_id),
            html.Div(dcc.Link("< Retour à l'arrêté", href=f'/{Endpoint.AM}/{am_id}')),
            _toggler(am_id),
            _am(am, buttons_hidden),
            _am_id(am_id),
            _buttons_hidden(buttons_hidden),
        ],
        className='pb-5',
    )


def _layout(am_id: str, with_buttons: Optional[str] = None) -> Component:
    return dbc.Spinner(_layout_if_logged(am_id, not with_buttons), id=_LAYOUT)


def _callbacks(app: Dash) -> None:
    editable_alineas_callbacks(app)
    editable_title_callbacks(app)

    @app.callback(
        Output(_LAYOUT, 'children'),
        Input(_delete_section_id(ALL), 'n_clicks'),
        Input(_add_section_id(ALL), 'n_clicks'),
        State(AM_ID, 'data'),
        State(_BUTTONS_HIDDEN, 'data'),
        prevent_initial_call=True,
    )
    def _delete_section(_, __, am_id: str, buttons_hidden):
        type_, section_id = extract_id_type_and_key_from_context()
        if type_ == _delete_section_id('')['type']:
            delete_am_section(am_id, section_id)
        elif type_ == _add_section_id('')['type']:
            insert_empty_section(am_id, section_id)
        return _layout_if_logged(am_id, buttons_hidden)


PAGE = Page(_layout, _callbacks, True)
