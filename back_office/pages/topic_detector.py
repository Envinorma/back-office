import json
import math
import random
from typing import Any, Dict, List, Optional

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash import Dash
from dash.dependencies import ALL, Input, Output
from dash.development.base_component import Component
from envinorma.models.arrete_ministeriel import ArreteMinisteriel
from envinorma.models.structured_text import StructuredText

from back_office.routing import Endpoint, Page
from back_office.utils import DATA_FETCHER, ensure_not_none, generate_id

_BATCH_SIZE = 10
_BATCH = generate_id(__file__, 'batch')


def _page_index(value: Any) -> Dict[str, Any]:
    return {'type': generate_id(__file__, 'page'), 'key': value}


def _topic_name(section: StructuredText) -> Optional[str]:
    topic = section.annotations.topic if section.annotations else None
    return topic.name if topic else None


def _title(section: StructuredText) -> Component:
    topic_name = _topic_name(section)
    badge = html.Span(topic_name, className='badge badge-primary') if topic_name else ''
    return html.Span([f'{section.title.text} ', badge], style={'font-size': '0.8em'})


def _section_topics(section: StructuredText) -> Component:
    style = {'margin-top': '3px', 'background-color': '#007bff33'} if _topic_name(section) else {}
    return html.Div(
        [_title(section), *[_section_topics(sub) for sub in section.sections]],
        style={'border-left': '3px solid #007bff', 'padding-left': '10px', **style},
    )


def _edit_button(am_id: str) -> Component:
    return dcc.Link(html.Button('Éditer les thèmes', className='btn btn-link'), href=f'/{Endpoint.EDIT_TOPICS}/{am_id}')


def _am_topics(am: ArreteMinisteriel, rank: int) -> Component:
    content = [
        html.H4(am.id),
        html.H6(am.title.text),
        _edit_button(am.id or ''),
        *[_section_topics(section) for section in am.sections],
    ]
    return dbc.Tab(content, label=rank + 1, labelClassName='small')


def _fetch_am_id_batch(batch_index: int, batch_size: int) -> List[str]:
    am_ids = sorted(DATA_FETCHER.load_all_am_metadata())
    random.seed(42)
    random.shuffle(am_ids)
    return am_ids[batch_index * batch_size : (batch_index + 1) * batch_size]


def _load_and_enrich_ams(batch_index: int, batch_size: int) -> List[ArreteMinisteriel]:
    am_ids = _fetch_am_id_batch(batch_index, batch_size)
    return [ensure_not_none(DATA_FETCHER.load_most_advanced_am(am_id)) for am_id in am_ids]


def _page_button(index: int, active_index: int) -> Component:
    return dbc.Button(index + 1, id=_page_index(index), className='btn-light', active=index == active_index)


def _nav(active_batch_index: int) -> Component:
    nb_batches = int(math.ceil(len(DATA_FETCHER.load_all_am_metadata()) / _BATCH_SIZE))
    pages = [
        dbc.Button('Batch n°', disabled=True),
        *[_page_button(batch_index, active_batch_index) for batch_index in range(nb_batches)],
    ]
    return dbc.ButtonGroup(pages, className='pagination mb-3')


def _topics_tabs(batch_index: int) -> Component:
    ams = _load_and_enrich_ams(batch_index, _BATCH_SIZE)
    return html.Div(
        [_nav(batch_index), dbc.Tabs([_am_topics(am, rank) for rank, am in enumerate(ams)], className='mb-3')]
    )


def _topics() -> Component:
    return dbc.Spinner(_topics_tabs(0), id=_BATCH, fullscreen=True)


def _intro() -> Component:
    return html.Div('Thèmes associés par le détecteur de thèmes à chaque AM de la base.', className='mb-3')


def layout() -> Component:
    return html.Div([html.H3('Détecteur de thèmes.'), _intro(), _topics()])


def _callbacks(app: Dash) -> None:
    @app.callback(Output(_BATCH, 'children'), Input(_page_index(ALL), 'n_clicks'), prevent_initial_call=True)
    def _update_batch(_):
        batch_index = int(json.loads(dash.callback_context.triggered[0]['prop_id'].split('.')[0])['key'])
        return _topics_tabs(batch_index)


PAGE = Page(layout, _callbacks)
