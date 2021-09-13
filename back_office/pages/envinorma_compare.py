from enum import Enum
from typing import Callable, Optional

import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, dcc, html
from dash.development.base_component import Component
from envinorma.models import AMMetadata, ArreteMinisteriel
from leginorma import LegifranceRequestError

from back_office.components import error_component
from back_office.components.diff import diff_component
from back_office.helpers.aida import extract_aida_am
from back_office.helpers.diff import compute_am_diff
from back_office.helpers.legifrance import extract_legifrance_am
from back_office.routing import Endpoint, Page
from back_office.utils import DATA_FETCHER, ensure_not_none

_PREFIX = __file__.split('/')[-1].replace('.py', '').replace('_', '-')
_ARGS = _PREFIX + '-args'
_SPINNER = _PREFIX + '-spinner'


class CompareWith(Enum):
    AIDA = 'aida'
    LEGIFRANCE = 'legifrance'


def _md(am: ArreteMinisteriel) -> Optional[AMMetadata]:
    return DATA_FETCHER.load_am_metadata(ensure_not_none(am.id))


def _diff_component(
    am_source: ArreteMinisteriel, am_envinorma: ArreteMinisteriel, source_title: str, normalize_text: bool
) -> Component:
    differences = compute_am_diff(am_source, am_envinorma, normalize_text)
    return diff_component(differences, source_title, 'Version Envinorma')


def _legifrance_diff(am: ArreteMinisteriel, normalize_text: bool) -> Component:
    md = _md(am)
    if not md:
        return error_component('AM Metadata not found')
    try:
        legifrance_version = extract_legifrance_am(md.cid, fallback_to_non_consolidated=True)
    except LegifranceRequestError as exc:
        return error_component(f'Erreur lors de la récupération de la version Légifrance: {str(exc)}')
    return _diff_component(legifrance_version, am, 'Version Légifrance', normalize_text)


def _aida_diff(am: ArreteMinisteriel, normalize_text: bool) -> Component:
    md = _md(am)
    if not md:
        return error_component('AM Metadata not found')
    aida_version = extract_aida_am(md.aida_page, am_id=am.id or '')
    if not aida_version:
        return error_component('Erreur lors de la récupération de la version AIDA.')
    return _diff_component(aida_version, am, 'Version AIDA', normalize_text)


def _component_builder(compare_with: CompareWith) -> Callable[[ArreteMinisteriel, bool], Component]:
    if compare_with == CompareWith.LEGIFRANCE:
        return _legifrance_diff
    if compare_with == CompareWith.AIDA:
        return _aida_diff
    raise NotImplementedError


def _build_component(am_id: str, compare_with_str: str, normalize_str: str = '') -> Component:
    normalize = bool(normalize_str)
    try:
        compare_with = CompareWith(compare_with_str)
    except ValueError:
        return error_component(f'Unhandled comparision with {compare_with_str}')
    am = DATA_FETCHER.load_most_advanced_am(am_id)
    if not am:
        return error_component(f'AM with id {am_id} not found')
    try:
        builder = _component_builder(compare_with)
    except NotImplementedError:
        return error_component(f'Not implemented comparison with {compare_with}')
    return builder(am, normalize)


def _layout(am_id: str, compare_with: str, normalize: str = '') -> Component:
    toggle_wording = 'Comparer les textes bruts' if normalize else 'Comparer seulement les chiffres/lettres'
    prefix = f'/{Endpoint.AM_COMPARE}/{am_id}/{compare_with}'
    toggle_href = prefix if normalize else f'{prefix}/normalize'
    return html.Div(
        [
            dcc.Link("< Retour à l'arrêté", href=f'/{Endpoint.AM}/{am_id}'),
            dcc.Link(toggle_wording, href=toggle_href, className='btn btn-primary ml-3'),
            dbc.Spinner(children=html.Div(), id=_SPINNER),
            dcc.Store(data=[am_id, compare_with, normalize], id=_ARGS),
        ]
    )


def _callbacks(app_: Dash) -> None:
    @app_.callback(Output(_SPINNER, 'children'), Input(_ARGS, 'data'))
    def _define_diff_component(args):
        return _build_component(*args)


PAGE = Page(_layout, _callbacks, False)
