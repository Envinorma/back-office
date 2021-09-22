from typing import List

import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.development.base_component import Component
from envinorma.models.am_metadata import AMMetadata, AMState

from back_office.routing import Endpoint
from back_office.utils import DATA_FETCHER

_TABS = [
    (Endpoint.AM_APERCU, 'Aperçu'),
    (Endpoint.AM_METADATA, 'Métadonnées'),
    (Endpoint.AM_CONTENT, 'Contenu'),
    (Endpoint.PARAMETRIZATION, 'Paramétrage'),
    (Endpoint.TOPICS, 'Thèmes'),
]


def _alert(message) -> Component:
    return dbc.Alert(message, color='warning', className='mt-2 mb-3')


def _warning(am_metadata: AMMetadata) -> Component:
    if am_metadata.state == AMState.VIGUEUR:
        return html.Div()
    if am_metadata.state == AMState.ABROGE:
        return _alert('Cet arrêté est abrogé et ne sera pas exploité dans l\'application envinorma.')
    if am_metadata.state == AMState.DELETED:
        return _alert(
            'Cet arrêté a été supprimé et ne sera pas exploité dans l\'application envinorma. '
            f'Raison de la suppression :\n{am_metadata.reason_deleted}'
        )
    if am_metadata.state == AMState.EN_CREATION:
        return _alert(
            'Cet arrêté est en cours de création et ne sera pas exploité dans l\'application envinorma '
            'tant qu\'il ne sera pas déclaré comme en vigueur.'
        )
    raise NotImplementedError(f'Unhandled state {am_metadata.state}')


def _tabs(am: AMMetadata) -> List[Component]:
    am_id = am.cid
    return [dbc.NavLink(label, href=f'/{Endpoint.AM}/{am_id}/{href}', active='partial') for href, label in _TABS]


def _sidebar(am: AMMetadata, am_id: str) -> Component:
    style = {'color': '#dc3545'}
    return html.Div(
        [
            dcc.Link('< Retour à la liste', href=f'/{Endpoint.INDEX}'),
            html.Hr(),
            html.H5(f'AM {am_id}', className='mb-2', style={'font-size': '1em'}),
            dcc.Link("Supprimer l'arrêté", href=f'/{Endpoint.DELETE_AM}/{am_id}', style=style),
            _warning(am),
            html.Hr(),
            dbc.Nav(_tabs(am), vertical=True, pills=True),
        ],
        className='col-2 am-nav',
    )


def page_with_sidebar(component: Component, am_id: str) -> Component:
    am = DATA_FETCHER.load_am_metadata(am_id)
    if not am:
        return html.Div('404')
    sidebar = _sidebar(am, am_id)
    content = html.Div(html.Div(component, className='container'), className='col-10 pt-3')
    return html.Div(html.Div([sidebar, content], className='row'), className='container-fluid')
