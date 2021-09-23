import json
from typing import Any, Dict, List, Optional, Tuple, Union

import dash_bootstrap_components as dbc
from dash import ALL, Dash, Input, Output, State, callback_context, dcc, html
from dash.development.base_component import Component
from envinorma.models import Annotations, ArreteMinisteriel, StructuredText
from envinorma.topics.patterns import TopicName
from envinorma.topics.simple_topics import SIMPLE_ONTOLOGY

from back_office.components import error_component, success_component
from back_office.components.am_component import am_with_summary_component
from back_office.routing import Page, Routing
from back_office.utils import DATA_FETCHER, ensure_not_none, generate_id

_TOPICS = SIMPLE_ONTOLOGY.keys()
_AM_ID = generate_id(__file__, 'am-id')
_AM = generate_id(__file__, 'am')
_AM_STRUCTURE_STORE = generate_id(__file__, 'am-structure-store')
_TOPICS_DROPDOWN = generate_id(__file__, 'topics-dropdown')
_TOPIC_EDITION_OUTPUT = generate_id(__file__, 'topic-edition-output')
_AM_MODAL = generate_id(__file__, 'am-modal')
_AM_MODAL_TRIGGER = generate_id(__file__, 'am-modal-trigger')

_Section = Union[ArreteMinisteriel, StructuredText]


def _set_topic_id(section_id: Any) -> Dict[str, Any]:
    return {'type': generate_id(__file__, 'set-topic'), 'key': section_id}


def _delete_topic_id(section_id: Any) -> Dict[str, Any]:
    return {'type': generate_id(__file__, 'delete-topic'), 'key': section_id}


def _topic_name(section: StructuredText) -> Optional[str]:
    topic = section.annotations.topic if section.annotations else None
    return topic.name if topic else None


def _topic_badge(topic_name: str, section_id: str) -> Component:
    style = {'font-size': '0.9em', 'padding': '2px'}
    badge = html.Button(topic_name, className='btn btn-primary btn-sm m-1', style=style)
    delete_style = {**style, 'color': '#dc3545'}
    close_button = html.Button(
        'supprimer', className='btn btn-link btn-sm m-1', id=_delete_topic_id(section_id), style=delete_style
    )
    return html.Span([badge, close_button])


def _title(section: StructuredText) -> Component:
    topic_name = _topic_name(section)
    badge = _topic_badge(topic_name, section.id) if topic_name else ''
    return html.Span([f'{section.title.text} ', badge], style={'font-size': '0.8em'})


def _section_topics(section: StructuredText, depth: int = 0) -> Component:
    common_style = {'border-left': '3px solid #007bff', 'padding-left': '25px'}
    style = {'margin-top': '3px'} if _topic_name(section) else {}
    additional_class_name = ' section-with-defined-topic' if _topic_name(section) else ''
    return html.Div(
        [_title(section), *[_section_topics(sub, depth + 1) for sub in section.sections]],
        style={**common_style, **style},
        id=_set_topic_id(section.id),
        className='section-topics' + additional_class_name,
    )


def _am_topics(am: ArreteMinisteriel) -> Component:
    return html.Div([_section_topics(section) for section in am.sections])


def _link_to_am(am_id: str) -> Component:
    return dcc.Link(html.Button('< Retour', className='btn btn-link'), href=Routing.topics_path(am_id))


def _am_topics_with_loader(am: ArreteMinisteriel) -> Component:
    return html.Div(
        [
            html.H5("Structure de l'AM à éditer."),
            dbc.Spinner(_am_topics(am), id=_AM),
        ],
        className='col-9',
        style={'height': '80vh', 'overflow-y': 'auto', 'border-bottom': '2px gainsboro solid'},
    )


def _topics_dropdown() -> Component:
    values = [topic.value for topic in _TOPICS]
    options = [{'label': topic, 'value': topic} for topic in values]
    return html.Div(
        [
            html.H5('Thème à utiliser'),
            dcc.Dropdown(_TOPICS_DROPDOWN, options, value=values[0], className='mb-3 mt-3', clearable=False),
            html.P('Cliquer sur les paragraphes auxquels associer le thème sélectionné.'),
            html.Div(id=_TOPIC_EDITION_OUTPUT),
        ],
        style={'background-color': '#DDDDDD', 'border-radius': '5px'},
        className='p-3',
    )


def _am_structure(section: _Section, depth: int = 0) -> Dict[str, Any]:
    result = {
        key: value for subsection in section.sections for key, value in _am_structure(subsection, depth + 1).items()
    }
    result[section.id or ''] = depth
    return result


def _id_store(am: ArreteMinisteriel) -> Component:
    return html.Div([dcc.Store(data=_am_structure(am), id=_AM_STRUCTURE_STORE), dcc.Store(data=am.id, id=_AM_ID)])


def _am_modal(am: ArreteMinisteriel) -> Component:
    body = dbc.ModalBody(am_with_summary_component(am, first_level=3))
    header = dbc.ModalHeader()
    modal = dbc.Modal([header, body], id=_AM_MODAL, size='xl')
    trigger = html.Button('Consulter l\'AM', className='btn btn-primary mt-3', id=_AM_MODAL_TRIGGER)
    return html.Div([trigger, modal])


def _first_column(am_id: str, am: ArreteMinisteriel) -> Component:
    return html.Div([_link_to_am(am_id), _topics_dropdown(), _am_modal(am)], className='col-3')


def _layout(am_id: str) -> Component:
    am = DATA_FETCHER.load_am(am_id)
    if not am:
        return html.Div('404')
    return html.Div(
        [
            html.H3(f'AM {am_id} - Edition des thèmes'),
            html.Div([_first_column(am_id, am), _am_topics_with_loader(am)], className='row mt-3'),
            _id_store(am),
        ]
    )


def _extract_trigger_keys(triggered: List[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
    trigger_ids = [json.loads(trigger['prop_id'].split('.')[0]) for trigger in triggered]
    delete_topic_ids = [id_['key'] for id_ in trigger_ids if 'delete-topic' in id_['type']]
    set_topic_ids = [id_['key'] for id_ in trigger_ids if 'set-topic' in id_['type']]
    return delete_topic_ids, set_topic_ids


def _keep_deepest_id(section_ids: List[str], section_id_to_depth: Dict[str, int]) -> str:
    return sorted(section_ids, key=lambda section_id: section_id_to_depth[section_id])[-1]


class _EditionError(Exception):
    pass


def _has_topic(section: StructuredText) -> bool:
    return bool(section.annotations and section.annotations.topic)


def _ensure_sections_have_no_subtopics(sections: List[StructuredText]) -> None:
    for section in sections:
        if _has_topic(section):
            raise _EditionError("Impossible d'affecter le thème car une sous-section contient un thème.")
        _ensure_sections_have_no_subtopics(section.sections)


def _check_edition_is_permitted(section: StructuredText, topic: Optional[TopicName], ascendant_has_topic: bool) -> None:
    if not topic:  # Erasing a topic is always allowed
        return
    if ascendant_has_topic:
        raise _EditionError("Impossible d'affecter le thème car un section parente contient un thème.")
    _ensure_sections_have_no_subtopics(section.sections)


def _edit_section_topic(
    section: StructuredText,
    target_section_id: str,
    topic: Optional[TopicName],
    delete_topic: bool,
    ascendant_has_topic: bool = False,
) -> StructuredText:
    if section.id == target_section_id:
        if not delete_topic:
            _check_edition_is_permitted(section, topic, ascendant_has_topic)
        if not section.annotations:
            section.annotations = Annotations()
        section.annotations.topic = topic
    else:
        ascendant_has_topic = ascendant_has_topic or _has_topic(section)
        section.sections = [
            _edit_section_topic(sub, target_section_id, topic, delete_topic, ascendant_has_topic)
            for sub in section.sections
        ]
    return section


def _edit_am_topic(am_id: str, target_section: str, topic_name: Optional[str], delete_topic: bool) -> ArreteMinisteriel:
    am = DATA_FETCHER.load_am(am_id)
    if not am:
        raise ValueError('Expecting AM.')
    if not topic_name and not delete_topic:
        raise _EditionError('Aucun thème n\'est sélectionné.')
    topic = TopicName(topic_name) if topic_name else None
    am.sections = [_edit_section_topic(section, target_section, topic, delete_topic) for section in am.sections]
    DATA_FETCHER.upsert_am(am_id, am)
    return am


def _callbacks(app: Dash) -> None:
    @app.callback(
        Output(_AM_MODAL, 'is_open'),
        Input(_AM_MODAL_TRIGGER, 'n_clicks'),
        prevent_initial_call=True,
    )
    def toggle_am(_):
        return True

    @app.callback(
        Output(_TOPIC_EDITION_OUTPUT, 'children'),
        Output(_AM, 'children'),
        Input(_set_topic_id(ALL), 'n_clicks'),
        Input(_delete_topic_id(ALL), 'n_clicks'),
        State(_TOPICS_DROPDOWN, 'value'),
        State(_AM_STRUCTURE_STORE, 'data'),
        State(_AM_ID, 'data'),
        prevent_initial_call=True,
    )
    def _edit_topic(_, __, dropdown_value, am_structure, am_id):
        delete_topic_ids, set_topic_ids = _extract_trigger_keys(callback_context.triggered)
        if delete_topic_ids:
            am = _edit_am_topic(am_id, delete_topic_ids[0], None, True)
            return success_component('Le thème a été supprimé.'), _am_topics(am)
        target_section = _keep_deepest_id(set_topic_ids, am_structure)
        try:
            am = _edit_am_topic(am_id, target_section, dropdown_value, False)
        except _EditionError as exc:
            am = ensure_not_none(DATA_FETCHER.load_am(am_id))
            return error_component(str(exc)), _am_topics(am)
        return success_component(f'Section correctement affectée au thème {dropdown_value}.'), _am_topics(am)


def _page(am_id: str) -> Component:
    return html.Div(_layout(am_id), className='container mt-3')


PAGE = Page(_page, _callbacks, True)
