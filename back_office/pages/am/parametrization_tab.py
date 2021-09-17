from dash import dcc
from back_office.routing import Endpoint
import json
import random
import string
from collections import Counter
from typing import Any, Dict, List, Tuple, Union
import dash_bootstrap_components as dbc

from dash import ALL, Dash, Input, Output, State, html, callback_context
from dash.development.base_component import Component
from envinorma.models import AMMetadata, ArreteMinisteriel, StructuredText
from envinorma.models.am_applicability import AMApplicability
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


def _toggler_component(condition_name: str, condition_hash: str) -> Component:
    return html.Div(
        condition_name,
        className='alert alert-secondary font-size-sm condition-block',
        style={'font-size': '0.8em'},
        id=_condition_id(condition_hash),
    )


_ConditionOrWarning = Union[Condition, str]


def _condition_component(condition_or_warning: _ConditionOrWarning) -> Component:
    if isinstance(condition_or_warning, str):
        return _toggler_component(f'Warning: {condition_or_warning}', str(hash(condition_or_warning)))
    return _toggler_component(condition_or_warning.to_str(), str(hash(condition_or_warning)))


def _extract_conditions_with_occurrences(
    parametrization: Parametrization, am_applicability: AMApplicability
) -> List[Tuple[_ConditionOrWarning, int]]:
    warnings = [warning.text for warnings_ in parametrization.id_to_warnings.values() for warning in warnings_]
    condition_or_warnings = [*parametrization.extract_conditions(), *warnings, *am_applicability.warnings]
    if am_applicability.condition_of_inapplicability:
        condition_or_warnings.append(am_applicability.condition_of_inapplicability)
    return Counter(condition_or_warnings).most_common()


def _edit_parameters_button(am_id: str) -> Component:
    button_wording = 'Éditer le paramétrage'
    return dcc.Link(dbc.Button(button_wording, color='primary'), href=f'/{Endpoint.EDIT_PARAMETRIZATION}/{am_id}')


def _conditions_component(am_id: str, parametrization: Parametrization, am_applicability: AMApplicability) -> Component:
    conditions_with_occurrences = _extract_conditions_with_occurrences(parametrization, am_applicability)
    condition_items = [
        _condition_component(condition) for condition, _ in sorted(conditions_with_occurrences, key=lambda x: -x[-1])
    ]
    return html.Div(
        [
            _edit_parameters_button(am_id),
            html.H3('Conditions et warnings'),
            html.Div(condition_items if condition_items else 'Pas de conditions.'),
        ],
        style={'height': '75vh', 'overflow-y': 'auto'},
    )


def _condition_badge(condition_id: str, operation: str) -> Component:
    id_ = _badge_id(_random_id())
    return html.Span(operation, id=id_, className='badge badge-secondary ml-1', **{'data-condition-id': condition_id})


def _condition_badges(
    inapplicabilities: List[InapplicableSection], alternatives: List[AlternativeSection], warnings: List[AMWarning]
) -> Component:
    badges_1 = [_condition_badge(str(hash(inap.condition)), 'inapplicable') for inap in inapplicabilities]
    badges_2 = [_condition_badge(str(hash(alt.condition)), 'section modifiée') for alt in alternatives]
    badges_3 = [_condition_badge(str(hash(warning.text)), 'warning') for warning in warnings]
    return html.Span(badges_1 + badges_2 + badges_3)


def _title_with_badges(title: str, badges: Component) -> Component:
    return html.Span([f'{title} ', badges], style={'font-size': '0.8em'})


def _title(title: str, section_id: str, parametrization: Parametrization) -> Component:
    badges = _condition_badges(
        parametrization.id_to_inapplicabilities.get(section_id) or [],
        parametrization.id_to_alternative_sections.get(section_id) or [],
        parametrization.id_to_warnings.get(section_id) or [],
    )
    return _title_with_badges(title, badges)


def _title_whole_am(applicability: AMApplicability) -> Component:
    badges = [_condition_badge(str(hash(warning)), 'warning') for warning in applicability.warnings]
    if applicability.condition_of_inapplicability:
        badges.append(_condition_badge(str(hash(applicability.condition_of_inapplicability)), 'inapplicable'))
    return _title_with_badges('ARRÊTÉ', html.Span(badges))


def _section_summary(section: StructuredText, parametrization: Parametrization) -> Component:
    common_style = {'border-left': '3px solid #007bff', 'padding-left': '25px'}
    return html.Div(
        [
            _title(section.title.text, section.id, parametrization),
            *[_section_summary(sub, parametrization) for sub in section.sections],
        ],
        style=common_style,
    )


def _am_summary(am: ArreteMinisteriel, parametrization: Parametrization) -> Component:
    return html.Div(
        [
            _title_whole_am(am.applicability),
            *[_section_summary(section, parametrization) for section in am.sections],
        ]
    )


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
    am_applicability = am.applicability if am.applicability else AMApplicability()
    return html.Div(
        [
            html.Div(_conditions_component(am.id or '', parametrization, am_applicability), className='col-4'),
            html.Div(_am_summary_column(am, parametrization), className='col-8'),
        ],
        className='row',
    )


def _extract_trigger_key(triggered: List[Dict[str, Any]]) -> str:
    return json.loads(triggered[0]['prop_id'].split('.')[0])['key']


def _callbacks(app: Dash, tab_id: str) -> None:
    @app.callback(
        Output(_condition_id(ALL), 'className'),
        Input(_condition_id(ALL), 'n_clicks'),
        State(_condition_id(ALL), 'className'),
        State(_condition_id(ALL), 'id'),
        prevent_initial_call=True,
    )
    def _toggle_buttons(_, class_names: List[str], condition_ids: List[Dict]):
        triggered = _extract_trigger_key(callback_context.triggered)
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
        triggered = _extract_trigger_key(callback_context.triggered)
        new_class_names = [
            class_name.replace('badge-secondary', 'badge-primary')
            if condition_id == triggered
            else class_name.replace('badge-primary', 'badge-secondary')
            for class_name, condition_id in zip(class_names, condition_ids)
        ]
        return new_class_names


TAB = ('Paramétrage', _layout, _callbacks)
