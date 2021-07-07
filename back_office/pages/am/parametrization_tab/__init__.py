import dash_bootstrap_components as dbc
from dash import Dash
from dash.development.base_component import Component
from envinorma.models import AMMetadata

from .am_apply_parameters_tab import TAB as am_apply_parameters_tab
from .parameter_list_tab import TAB as parameter_list_tab

_SUB_TABS = [am_apply_parameters_tab, parameter_list_tab]


def _tabs(am: AMMetadata) -> Component:
    tabs = [
        dbc.Tab(layout(am), label=label, className='mt-3', tab_id=str(i))
        for i, (label, layout, _) in enumerate(_SUB_TABS)
    ]
    return dbc.Tabs(tabs, id='am-parametrization-tabs')


def _layout(am_metadata: AMMetadata) -> Component:
    return _tabs(am_metadata)


def _callbacks(app: Dash, tab_id: str) -> None:
    for _, _, callbacks in _SUB_TABS:
        callbacks(app)


TAB = ('Paramétrage', _layout, _callbacks)
