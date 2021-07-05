import json
from typing import Any, Dict, List, Optional, Union

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash import Dash
from dash.dependencies import ALL, Input, Output, State
from dash.development.base_component import Component
from envinorma.models import Annotations, ArreteMinisteriel, StructuredText
from envinorma.topics.patterns import TopicName
from envinorma.topics.simple_topics import SIMPLE_ONTOLOGY

from back_office.helpers.login import get_current_user
from back_office.routing import Endpoint, Page
from back_office.utils import DATA_FETCHER, generate_id

_TOPICS = SIMPLE_ONTOLOGY.keys()
_NO_TOPIC = 'no-topic'
_AM_ID = generate_id(__file__, 'am-id')
_AM = generate_id(__file__, 'am')
_AM_STRUCTURE_STORE = generate_id(__file__, 'am-structure-store')
_TOPICS_DROPDOWN = generate_id(__file__, 'topics-dropdown')
_TOPIC_EDITION_OUTPUT = generate_id(__file__, 'topic-edition-output')
_Section = Union[ArreteMinisteriel, StructuredText]


def _section_id(section_id: Any) -> Dict[str, Any]:
    return {'type': generate_id(__file__, 'section-id'), 'key': section_id}


def _topic_name(section: StructuredText) -> Optional[str]:
    topic = section.annotations.topic if section.annotations else None
    return topic.name if topic else None


def _title(section: StructuredText) -> Component:
    topic_name = _topic_name(section)
    badge = html.Span(topic_name, className='badge badge-primary') if topic_name else ''
    return html.Span([f'{section.title.text} ', badge], style={'font-size': '0.8em'})


def _section_topics(section: StructuredText, depth: int = 0) -> Component:
    common_style = {'border-left': '3px solid #007bff', 'padding-left': '25px'}
    style = {'margin-top': '3px'} if _topic_name(section) else {}
    additional_class_name = ' section-with-defined-topic' if _topic_name(section) else ''
    return html.Div(
        [_title(section), *[_section_topics(sub, depth + 1) for sub in section.sections]],
        style={**common_style, **style},
        id=_section_id(section.id),
        className='section-topics' + additional_class_name,
    )


def _am_topics(am: ArreteMinisteriel) -> Component:
    return html.Div([_section_topics(section) for section in am.sections])


def _link_to_am(am_id: str) -> Component:
    return dcc.Link(html.Button("Consulter l'AM", className='btn btn-link'), href=f'/{Endpoint.AM}/{am_id}')


def _am_topics_with_loader(am: ArreteMinisteriel) -> Component:
    return html.Div(
        [
            html.H5("Structure de l'AM à éditer."),
            _link_to_am(am.id or ''),
            dbc.Spinner(_am_topics(am), id=_AM),
        ],
        className='col-9',
        style={'height': '80vh', 'overflow-y': 'auto', 'border-bottom': '2px gainsboro solid'},
    )


def _topics_dropdown() -> Component:
    options = [{'label': topic.value, 'value': topic.value} for topic in _TOPICS]
    options.append({'label': _NO_TOPIC, 'value': _NO_TOPIC})
    return html.Div(
        html.Div(
            [
                html.H5('Thème à utiliser'),
                dcc.Dropdown(_TOPICS_DROPDOWN, options, value=_NO_TOPIC, className='mb-3 mt-3'),
                html.P('Cliquer sur les paragraphes auxquels associer le thème sélectionné.'),
                html.Div(id=_TOPIC_EDITION_OUTPUT),
            ],
            style={'background-color': '#DDDDDD', 'border-radius': '5px'},
            className='p-3',
        ),
        className='col-3',
    )


def _am_structure(section: _Section, depth: int = 0) -> Dict[str, Any]:
    result = {
        key: value for subsection in section.sections for key, value in _am_structure(subsection, depth + 1).items()
    }
    result[section.id or ''] = depth
    return result


def _id_store(am: ArreteMinisteriel) -> Component:
    return html.Div([dcc.Store(data=_am_structure(am), id=_AM_STRUCTURE_STORE), dcc.Store(data=am.id, id=_AM_ID)])


def _layout_if_logged(am_id: str) -> Component:
    am = DATA_FETCHER.load_structured_am(am_id)
    if not am:
        return html.Div('404')
    return html.Div(
        [
            html.H3(f'AM {am_id} - Edition des thèmes'),
            html.Div([_topics_dropdown(), _am_topics_with_loader(am)], className='row mt-3'),
            _id_store(am),
        ]
    )


def _layout(am_id: str) -> Component:
    if not get_current_user().is_authenticated:
        return dcc.Location(pathname='/login', id='login-redirect')
    return _layout_if_logged(am_id)


def _extract_trigger_keys(triggered: List[Dict[str, Any]]) -> List[str]:
    return [json.loads(trigger['prop_id'].split('.')[0])['key'] for trigger in triggered]


def _keep_deepest_id(section_ids: List[str], section_id_to_depth: Dict[str, int]) -> str:
    return sorted(section_ids, key=lambda section_id: section_id_to_depth[section_id])[-1]


def _edit_section_topic(section: StructuredText, target_section_id: str, topic: Optional[TopicName]) -> StructuredText:
    if section.id == target_section_id:
        if not section.annotations:
            section.annotations = Annotations()
        section.annotations.topic = topic
    else:
        section.sections = [_edit_section_topic(sub, target_section_id, topic) for sub in section.sections]
    return section


def _edit_am_topic(am_id: str, target_section: str, topic_name: str) -> ArreteMinisteriel:
    am = DATA_FETCHER.load_structured_am(am_id)
    if not am:
        raise ValueError('Expecting AM.')
    topic = TopicName(topic_name) if topic_name != _NO_TOPIC else None
    am.sections = [_edit_section_topic(section, target_section, topic) for section in am.sections]
    DATA_FETCHER.upsert_structured_am(am_id, am)
    return am


def _callbacks(app: Dash) -> None:
    @app.callback(
        Output(_TOPIC_EDITION_OUTPUT, 'children'),
        Output(_AM, 'children'),
        Input(_section_id(ALL), 'n_clicks'),
        State(_TOPICS_DROPDOWN, 'value'),
        State(_AM_STRUCTURE_STORE, 'data'),
        State(_AM_ID, 'data'),
        prevent_initial_call=True,
    )
    def _edit_topic(_, dropdown_value, am_structure, am_id):
        section_ids = _extract_trigger_keys(dash.callback_context.triggered)
        target_section = _keep_deepest_id(section_ids, am_structure)
        am = _edit_am_topic(am_id, target_section, dropdown_value)
        return dbc.Alert(f'Section {target_section} affectée au thème {dropdown_value}.'), _am_topics(am)


PAGE = Page(_layout, _callbacks)
