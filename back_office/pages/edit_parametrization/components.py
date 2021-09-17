from typing import List, Optional

import dash_bootstrap_components as dbc
from dash import html
from dash.development.base_component import Component
from envinorma.io.markdown import extract_markdown_text
from envinorma.models import Condition, EnrichedString, StructuredText
from envinorma.parametrization import AlternativeSection, AMWarning, InapplicableSection
from envinorma.parametrization.models.parametrization import ParameterElement

from back_office.components import ButtonState, link_button
from back_office.components.am_component import table_to_component
from back_office.components.diff import diff_component
from back_office.helpers.diff import compute_text_diff
from back_office.routing import Endpoint


def condition_str(condition: Condition) -> Component:
    return html.Span(f'Si {condition.to_str()}')


def _human_alinea_tuple(ints: Optional[List[int]]) -> str:
    if not ints:
        return 'Tous'
    return ', '.join(map(str, map(lambda x: x + 1, sorted(ints))))


def _alinea_to_component(alinea: EnrichedString, inactive: bool) -> Component:
    if alinea.text:
        return html.P(alinea.text, className='inactive' if inactive else '')
    if alinea.table:
        return table_to_component(alinea.table, None)
    return html.Span()


def _alineas_to_component(targeted_alineas: Optional[List[int]], alineas: List[EnrichedString]) -> Component:
    return html.Div(
        [
            _alinea_to_component(alinea, targeted_alineas is None or i in targeted_alineas)
            for i, alinea in enumerate(alineas)
        ],
        className='diff',
    )


def _inapplicability(
    am_id: str, inapplicability: InapplicableSection, text: Optional[StructuredText], color: str
) -> Component:
    alineas = html.Div(
        [
            f'Alineas visés : {_human_alinea_tuple(inapplicability.alineas)}',
            _alineas_to_component(inapplicability.alineas, text.outer_alineas) if text else html.Span(),
        ]
    )
    condition = condition_str(inapplicability.condition)
    href = f'/{Endpoint.ADD_INAPPLICABILITY}/{am_id}/{inapplicability.id}'
    edit = link_button('Éditer ou supprimer', href=href, state=ButtonState.NORMAL_LINK)
    copy = link_button('Copier', href=f'{href}/copy', state=ButtonState.NORMAL_LINK)
    buttons = html.Div([edit, copy])
    return dbc.Card(
        [dbc.CardHeader('Section potentiellement inapplicable'), dbc.CardBody([condition, alineas, buttons])],
        color=color,
        outline=True,
        className='mb-2',
    )


def _alternative_section(
    am_id: str, alternative_section: AlternativeSection, text: Optional[StructuredText], color: str
) -> Component:
    condition = condition_str(alternative_section.condition)
    if text:
        differences = compute_text_diff(text, alternative_section.new_text)
        new_version = diff_component(differences, 'Version initiale', 'Version modifiée')
    else:
        new_version = html.Div(
            list(map(html.P, extract_markdown_text(alternative_section.new_text, 1))), className='diff'
        )
    href = f'/{Endpoint.ADD_ALTERNATIVE_SECTION}/{am_id}/{alternative_section.id}'
    edit = link_button('Éditer ou supprimer', href=href, state=ButtonState.NORMAL_LINK)
    copy = link_button('Copier', href=f'{href}/copy', state=ButtonState.NORMAL_LINK)
    buttons = html.Div([edit, copy])
    return dbc.Card(
        [dbc.CardHeader('Section alternative'), dbc.CardBody([condition, new_version, buttons])],
        color=color,
        outline=True,
        className='mb-2',
    )


def _warning(am_id: str, warning: AMWarning, color: str) -> Component:
    href = f'/{Endpoint.ADD_WARNING}/{am_id}/{warning.id}'
    edit = link_button('Éditer ou supprimer', href=href, state=ButtonState.NORMAL_LINK)
    copy = link_button('Copier', href=f'{href}/copy', state=ButtonState.NORMAL_LINK)
    buttons = html.Div([edit, copy])
    return dbc.Card(
        [dbc.CardHeader('Avertissement'), dbc.CardBody([warning.text, buttons])],
        color=color,
        outline=True,
        className='mb-2',
    )


def parameter_component(
    am_id: str, element: ParameterElement, text: Optional[StructuredText], color: str = 'dark'
) -> Component:
    if isinstance(element, InapplicableSection):
        return _inapplicability(am_id, element, text, color)
    if isinstance(element, AlternativeSection):
        return _alternative_section(am_id, element, text, color)
    if isinstance(element, AMWarning):
        return _warning(am_id, element, color)
    raise ValueError(f'Unknown parameter type {type(element)}')
