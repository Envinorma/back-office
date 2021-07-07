from typing import Optional

import dash_bootstrap_components as dbc
import dash_html_components as html
from dash import Dash
from dash.development.base_component import Component
from envinorma.models.am_metadata import AMMetadata, AMState

from back_office.routing import Page
from back_office.utils import DATA_FETCHER

from .am_versions_tab import TAB as am_versions_tab
from .compare_tab import TAB as compare_tab
from .default_content_tab import TAB as default_content_tab
from .metadata_tab import TAB as metadata_tab
from .parametrization_tab import TAB as parametrization_tab
from .topics_tab import TAB as topics_tab

_TABS = [metadata_tab, default_content_tab, am_versions_tab, parametrization_tab, compare_tab, topics_tab]


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


def _layout(am_id: str, tab: Optional[str] = None) -> Component:
    am = DATA_FETCHER.load_am_metadata(am_id)
    if not am:
        return html.Div('404')
    return html.Div([html.H3(f'AM {am.cid}'), _warning(am), _tabs(am, tab)])


def _callbacks(app: Dash) -> None:
    for _, _, callbacks in _TABS:
        callbacks(app)


PAGE = Page(_layout, _callbacks)
