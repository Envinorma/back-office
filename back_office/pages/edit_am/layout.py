from typing import Optional, Tuple

import dash_bootstrap_components as dbc
import dash_editable_div as ded
from dash import dcc, html
from dash.development.base_component import Component
from envinorma.models import AMMetadata, ArreteMinisteriel

from back_office.routing import Endpoint
from back_office.utils import DATA_FETCHER

from . import ids
from .components import text_area_value


def _title_component(am_id: str, am_metadata: AMMetadata) -> Component:
    human_am_id = (am_metadata.nor or am_metadata.cid) if am_metadata else am_id
    title = html.H3(f'Édition de l\'AM {human_am_id}')
    am_backlink = html.P(dcc.Link('< Retour', href=f'/{Endpoint.AM}/{am_id}/{Endpoint.AM_CONTENT}'))
    return html.Div([title, am_backlink])


def _buttons() -> Component:
    btn_class = 'btn btn-secondary btn-light'
    body = dbc.ModalBody(html.P('Les modifications actuelles seront perdues. Procéder quand même ?'))
    footer = dbc.ModalFooter(
        html.Button('Confirmer l\'opération', id=ids.AIDA_LEGIFRANCE_CONFIRM, className='btn btn-primary')
    )
    modal = dbc.Modal([body, footer], id=ids.AIDA_LEGIFRANCE_MODAL)
    return html.Div(
        [
            html.Button('Remplacer par la version Légifrance', id=ids.FETCH_LEGIFRANCE, className=f'{btn_class} mr-2'),
            html.Button('Remplacer par la version AIDA', id=ids.FETCH_AIDA, className=btn_class),
            modal,
            dcc.Store(id=ids.FROM_LEGIFRANCE_OR_AIDA, data=''),
        ],
        className='mb-3 mt-3',
    )


def _structure_edition_component(am: Optional[ArreteMinisteriel]) -> Component:
    return ded.EditableDiv(
        id=ids.TEXT_AREA_COMPONENT,
        children=text_area_value(am) if am else [],
        className='text',
        style={'padding': '10px', 'border': '1px solid rgba(0,0,0,.1)', 'border-radius': '5px'},
    )


def _toc() -> Component:
    return html.Div(dbc.Spinner(html.Div(id=ids.TOC_COMPONENT)), className='summary')


def _get_main_row(am: Optional[ArreteMinisteriel]) -> Component:
    first_column = html.Div(className='col-3', children=[_toc()])
    second_column = html.Div(_structure_edition_component(am), className='col-9')
    return html.Div([first_column, second_column], className='row mb-5')


def _am_component(am: Optional[ArreteMinisteriel]) -> Component:
    return _get_main_row(am)


def _diff_modal() -> Tuple[Component, Component]:
    text = 'Vérifier les modifications.'
    modal_components = [dbc.ModalHeader(text), dbc.ModalBody(dbc.Spinner('', id=ids.DIFF_BODY))]
    modal = dbc.Modal(modal_components, id=ids.DIFF_MODAL, size='xl')
    trigger_button = html.Button(text, id=ids.DIFF_BUTTON, className='btn btn-light save-button mr-2 button-shadow')
    return trigger_button, modal


def _save_modal() -> Tuple[Component, Component]:
    modal_components = [
        dbc.ModalHeader('Enregistrement'),
        dbc.ModalBody(html.Div('', id=ids.SAVE_MODAL_BODY)),
        dbc.ModalFooter(html.Button('Valider', id=ids.SAVE_BUTTON, className='btn btn-primary')),
    ]
    modal = dbc.Modal(modal_components, id=ids.SAVE_MODAL, size='xl')
    trigger_button = html.Button(
        'Enregistrer', id=ids.PRESAVE_BUTTON, className='btn btn-primary save-button button-shadow'
    )
    return trigger_button, modal


def _save_output() -> Component:
    return html.Div('', id=ids.SAVE_OUTPUT, className='aida-output')


def _save() -> Component:
    diff_trigger_button, diff_modal = _diff_modal()
    save_trigger_button, save_modal = _save_modal()
    return html.Div([diff_trigger_button, diff_modal, save_trigger_button, save_modal], className='save-zone')


def _aida_legifrance_output() -> Component:
    return html.Div('', id=ids.AIDA_LEGIFRANCE_OUTPUT, className='aida-output')


def _hidden_btn() -> Component:
    return html.Button('', id=ids.HIDDEN_BUTTON, hidden=True)


def _page_content(am_id: str, am: Optional[ArreteMinisteriel]) -> Component:
    am_id_store = dcc.Store(id=ids.AM_ID, data=am_id)
    component = _am_component(am)
    return html.Div([component, _save(), _aida_legifrance_output(), _save_output(), am_id_store, _hidden_btn()])


def layout(am_id: str) -> Component:
    am_metadata = DATA_FETCHER.load_am_metadata(am_id)
    if not am_metadata:
        return html.P(f'404 - Arrêté {am_id} inconnu')
    am = DATA_FETCHER.load_am(am_id)
    return html.Div(
        [_title_component(am_id, am_metadata), _buttons(), _page_content(am_id, am)], className='container mt-3'
    )
