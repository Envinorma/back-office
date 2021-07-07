import json
import random
import string
from collections import Counter
from typing import Any, Dict, List, Tuple, Union

import dash
import dash_html_components as html
from dash import Dash
from dash.dependencies import ALL, Input, Output, State
from dash.development.base_component import Component
from envinorma.models import AMMetadata, ArreteMinisteriel, Ints, StructuredText
from envinorma.parametrization.models import (
    AlternativeSection,
    AMWarning,
    Condition,
    InapplicableSection,
    Parametrization,
)

from back_office.utils import DATA_FETCHER, generate_id


def _condition_id(condition_id: Any) -> Dict[str, Any]:
    return {'type': generate_id(__file__, 'condition-id'), 'key': condition_id}


def _badge_id(badge_id: Any) -> Dict[str, Any]:
    return {'type': generate_id(__file__, 'badge-id'), 'key': badge_id}


def _random_id(size: int = 12) -> str:
    return ''.join([random.choice(string.ascii_letters) for _ in range(size)])  # noqa: S311


def _condition_component(condition: Condition) -> Component:
    return html.Div(
        condition.to_str(),
        className='alert alert-secondary font-size-sm condition-block',
        style={'font-size': '0.8em'},
        id=_condition_id(str(hash(condition))),
    )


def _conditions_component(parametrization: Parametrization) -> Component:
    counter: List[Tuple[Condition, int]] = Counter(parametrization.extract_conditions()).most_common()
    conditions: List[Condition] = [cd for cd, _ in sorted(counter, key=lambda x: -x[1])]
    condition_items = [_condition_component(condition) for condition in conditions]

    return html.Div(
        [html.H3('Conditions'), html.Div(condition_items if condition_items else 'Pas de conditions.')],
        style={'height': '75vh', 'overflow-y': 'auto'},
    )


def _condition_badge(condition: Condition, operation: str) -> Component:
    id_ = _badge_id(_random_id())
    return html.Span(
        operation, id=id_, className='badge badge-secondary ml-1', **{'data-condition-id': str(hash(condition))}
    )


def _condition_badges(
    inapplicabilities: List[InapplicableSection], alternatives: List[AlternativeSection], warnings: List[AMWarning]
) -> Component:
    badges_1 = [_condition_badge(inap.condition, 'inapplicable') for inap in inapplicabilities]
    badges_2 = [_condition_badge(alt.condition, 'section modifiée') for alt in alternatives]
    badges_3: List[Component] = [html.Span('warning', className='badge badge-secondary ml-1') for _ in warnings]
    return html.Span(badges_1 + badges_2 + badges_3)


def _title(section: StructuredText, path: Ints, parametrization: Parametrization) -> Component:
    badges = _condition_badges(
        parametrization.path_to_conditions.get(path) or [],
        parametrization.path_to_alternative_sections.get(path) or [],
        parametrization.path_to_warnings.get(path) or [],
    )
    return html.Span([f'{section.title.text} ', badges], style={'font-size': '0.8em'})


def _section_summary(
    section: StructuredText, id_to_path: Dict[str, Ints], parametrization: Parametrization
) -> Component:
    common_style = {'border-left': '3px solid #007bff', 'padding-left': '25px'}
    return html.Div(
        [
            _title(section, id_to_path[section.id], parametrization),
            *[_section_summary(sub, id_to_path, parametrization) for sub in section.sections],
        ],
        style=common_style,
    )


_Section = Union[ArreteMinisteriel, StructuredText]


def _id_to_path(section: _Section, prefix: Ints = ()) -> Dict[str, Ints]:
    result = {
        key: value
        for i, child in enumerate(section.sections)
        for key, value in _id_to_path(child, prefix + (i,)).items()
    }
    result[section.id or ''] = prefix
    return result


def _am_summary(am: ArreteMinisteriel, parametrization: Parametrization) -> Component:
    id_to_path = _id_to_path(am)
    return html.Div([_section_summary(section, id_to_path, parametrization) for section in am.sections])


def _am_summary_column(am: ArreteMinisteriel, parametrization: Parametrization) -> Component:
    return html.Div(
        _am_summary(am, parametrization),
        style={'height': '75vh', 'overflow-y': 'auto', 'border-bottom': '2px gainsboro solid'},
    )


def _layout(am_metadata: AMMetadata) -> Component:
    am = DATA_FETCHER.load_most_advanced_am(am_metadata.cid)
    if not am:
        return html.Div('AM non initialisé.')
    parametrization = DATA_FETCHER.load_or_init_parametrization(am_metadata.cid)
    return html.Div(
        [
            html.Div(_conditions_component(parametrization), className='col-4'),
            html.Div(_am_summary_column(am, parametrization), className='col-8'),
        ],
        className='row',
    )


def _extract_trigger_key(triggered: List[Dict[str, Any]]) -> str:
    return json.loads(triggered[0]['prop_id'].split('.')[0])['key']


def _callbacks(app: Dash) -> None:
    @app.callback(
        Output(_condition_id(ALL), 'className'),
        Input(_condition_id(ALL), 'n_clicks'),
        State(_condition_id(ALL), 'className'),
        State(_condition_id(ALL), 'id'),
        prevent_initial_call=True,
    )
    def _toggle_buttons(_, class_names: List[str], condition_ids: List[Dict]):
        triggered = _extract_trigger_key(dash.callback_context.triggered)
        keys = [cd['key'] for cd in condition_ids]
        new_class_names = [
            class_name.replace('alert-secondary', 'alert-primary')
            if condition_id == triggered
            else class_name.replace('alert-primary', 'alert-secondary')
            for class_name, condition_id in zip(class_names, keys)
        ]
        return new_class_names

    @app.callback(
        Output(_badge_id(ALL), 'className'),
        Input(_condition_id(ALL), 'n_clicks'),
        State(_badge_id(ALL), 'className'),
        State(_badge_id(ALL), 'data-condition-id'),
        prevent_initial_call=True,
    )
    def _toggle_badges(_, class_names: List[str], condition_ids: List[str]):
        triggered = _extract_trigger_key(dash.callback_context.triggered)
        new_class_names = [
            class_name.replace('badge-secondary', 'badge-primary')
            if condition_id == triggered
            else class_name.replace('badge-primary', 'badge-secondary')
            for class_name, condition_id in zip(class_names, condition_ids)
        ]
        return new_class_names


TAB = ("Liste des paramètres", _layout, _callbacks)
