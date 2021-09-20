from typing import Optional

import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, State, dcc, html
from dash.development.base_component import Component
from envinorma.enriching import add_metadata
from envinorma.models import AMMetadata
from envinorma.parametrization.apply_parameter_values import AMWithApplicability, build_am_with_applicability

from back_office.components.parametric_am import parametric_am_callbacks, parametric_am_component
from back_office.utils import DATA_FETCHER, ensure_not_none

_PREFIX = 'default-content-tab'
_AM = f'{_PREFIX}-am'
_TAB = f'{_PREFIX}-tab'
_AM_ID = f'{_PREFIX}-am-id'


def _am_component(am: AMWithApplicability, am_metadata: AMMetadata) -> Component:
    if not am.arrete.legifrance_url:
        am.arrete = add_metadata(am.arrete, ensure_not_none(am_metadata))
    return parametric_am_component(am, _PREFIX, with_topics=False)


def _am_component_with_toc(am: Optional[AMWithApplicability], am_metadata: AMMetadata) -> Component:
    if not am:
        return dbc.Alert('404 - AM non initialisé.', color='warning', className='mb-3 mt-3')
    return html.Div(_am_component(am, am_metadata), id=_AM)


def _load_default_am(am_id) -> Optional[AMWithApplicability]:
    am = DATA_FETCHER.load_am(am_id)
    if not am:
        return None
    parametrization = DATA_FETCHER.load_or_init_parametrization(am_id)
    return build_am_with_applicability(am, parametrization, {})


def _main_component(am_id: str) -> Component:
    am_metadata = DATA_FETCHER.load_am_metadata(am_id)
    if not am_metadata:
        return html.Div()
    return _am_component_with_toc(_load_default_am(am_metadata.cid), am_metadata)


def _layout(am_metadata: AMMetadata) -> Component:
    return html.Div(
        [
            dbc.Spinner(html.Div(), id=_TAB),
            dcc.Store(data=am_metadata.cid, id=_AM_ID),
        ]
    )


def _callbacks(app: Dash, tab_id: str) -> None:
    parametric_am_callbacks(app, _PREFIX)

    @app.callback(Output(_TAB, 'children'), Input('am-tabs', 'active_tab'), State(_AM_ID, 'data'))
    def load_main_component(active_tab: str, am_id: str):
        if active_tab == str(tab_id):
            return _main_component(am_id)
        return html.Div()


TAB = ('Version par défaut', _layout, _callbacks)
