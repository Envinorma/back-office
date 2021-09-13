from typing import Optional

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_editable_div as ded
import dash_html_components as html
from dash.development.base_component import Component
from envinorma.models import AMMetadata, ArreteMinisteriel

from back_office.routing import Endpoint
from back_office.utils import DATA_FETCHER

from . import ids
from .components import text_area_value


def _title_component(am_id: str, am_metadata: AMMetadata) -> Component:
    human_am_id = (am_metadata.nor or am_metadata.cid) if am_metadata else am_id
    title = html.H3(f'Édition de l\'AM {human_am_id}')
    am_backlink = html.P(dcc.Link('< Retour', href=f'/{Endpoint.AM}/{am_id}'))
    return html.Div([title, am_backlink])


def _buttons() -> Component:
    btn_class = 'btn btn-secondary btn-light'
    return html.Div(
        [
            html.Button('Remplacer par la version Légifrance', id=ids.FETCH_LEGIFRANCE, className=f'{btn_class} mr-2'),
            html.Button('Remplacer par la version AIDA', id=ids.FETCH_AIDA, className=btn_class),
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


def _save_button() -> Component:
    return html.Button('Enregistrer', id=ids.SAVE_BUTTON, className='btn btn-primary save-button')


def _save_output() -> Component:
    return html.Div('', id=ids.SAVE_OUTPUT)


def _save() -> Component:
    return html.Div([_save_button(), _save_output()], className='save-zone')


def _aida_output() -> Component:
    return html.Div('', id=ids.AIDA_OUTPUT, className='aida-output')


def _page_content(am_id: str, am: Optional[ArreteMinisteriel]) -> Component:
    am_id_store = dcc.Store(id=ids.AM_ID, data=am_id)
    component = _am_component(am)
    return html.Div([component, _save(), _aida_output(), am_id_store])


def layout(am_id: str) -> Component:
    am_metadata = DATA_FETCHER.load_am_metadata(am_id)
    if not am_metadata:
        return html.P(f'404 - Arrêté {am_id} inconnu')
    am = DATA_FETCHER.load_most_advanced_am(am_id)
    return html.Div([_title_component(am_id, am_metadata), _buttons(), _page_content(am_id, am)])
