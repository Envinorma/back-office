from typing import Callable, List, Optional, Tuple

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash import Dash
from dash.dependencies import Input, Output, State
from dash.development.base_component import Component
from envinorma.models.am_metadata import AMMetadata, AMState

from back_office.routing import Endpoint, Page
from back_office.utils import DATA_FETCHER

from .am_versions_tab import TAB as am_versions_tab
from .compare_tab import TAB as compare_tab
from .default_content_tab import TAB as default_content_tab
from .metadata_tab import TAB as metadata_tab
from .parametrization_tab import TAB as parametrization_tab
from .topics_tab import TAB as topics_tab

_Tab = Tuple[str, Callable[[AMMetadata], Component], Callable[[Dash, str], None]]
_TABS: List[_Tab] = [metadata_tab, default_content_tab, am_versions_tab, parametrization_tab, compare_tab, topics_tab]

_AM_ID = 'am-tabs-am-id'


def _warning(am_metadata: AMMetadata) -> Component:
    if am_metadata.state == AMState.VIGUEUR:
        return html.Div()
    if am_metadata.state == AMState.ABROGE:
        return dbc.Alert(
            'Cet arrêté est abrogé et ne sera pas exploité dans l\'application envinorma.', color='warning'
        )
    if am_metadata.state == AMState.DELETED:
        return dbc.Alert(
            f'Cet arrêté a été supprimé et ne sera pas exploité dans l\'application envinorma. '
            f'Raison de la suppression :\n{am_metadata.reason_deleted}',
            color='warning',
        )
    raise NotImplementedError(f'Unhandled state {am_metadata.state}')


def _tabs(am: AMMetadata, default_tab_id: Optional[str]) -> Component:
    tabs = [
        dbc.Tab(layout(am), label=label, className='mt-3', tab_id=str(i)) for i, (label, layout, _) in enumerate(_TABS)
    ]
    return dbc.Tabs(tabs, id='am-tabs', active_tab=default_tab_id or '0')


def _clean_am_id(am_id: str) -> str:
    for regime in 'AED':
        if am_id.endswith(f'_{regime}'):
            return am_id[:-2]
    return am_id


def _layout(am_id: str, tab: Optional[str] = None) -> Component:
    am_id = _clean_am_id(am_id)
    am = DATA_FETCHER.load_am_metadata(am_id)
    if not am:
        return html.Div('404')
    return html.Div([dcc.Store(data=am_id, id=_AM_ID), html.H3(f'AM {am.cid}'), _warning(am), _tabs(am, tab)])


def _callbacks(app: Dash) -> None:
    for tab_rank, (_, _, callbacks) in enumerate(_TABS):
        callbacks(app, str(tab_rank))

    @app.callback(
        Output('url', 'href'), Input('am-tabs', 'active_tab'), State(_AM_ID, 'data'), prevent_initial_call=True
    )
    def load_main_component(active_tab: str, am_id: str):
        return f'/{Endpoint.AM}/{am_id}/{active_tab}'


PAGE = Page(_layout, _callbacks)
