from collections import Counter
from typing import Dict, Union

import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.development.base_component import Component
from envinorma.models import AMMetadata, AMState, Classement

from back_office.components.upload_ams import upload_ams_callbacks, upload_ams_component
from back_office.helpers.login import get_current_user
from back_office.routing import Endpoint, Page
from back_office.utils import AM_ID_TO_NB_CLASSEMENTS, DATA_FETCHER


def _get_str_classement(classement: Classement) -> str:
    if classement.alinea:
        return f'{classement.rubrique}-{classement.regime.value}-al.{classement.alinea}'
    return f'{classement.rubrique}-{classement.regime.value}'


def _am_descriptor(md: AMMetadata) -> str:
    classements_list = [_get_str_classement(classement) for classement in md.classements]
    if md.nickname:
        classements_list.append(md.nickname)
    return ', '.join(classements_list)


def _normal_td(content: Union[Component, str, int]) -> Component:
    return html.Td(content, className='align-middle', style={'font-size': '0.85em'})


def _is_transverse_cell(is_transverse: bool) -> Component:
    return html.Td('☑️' if is_transverse else '')


def _get_row(rank: int, am: AMMetadata) -> Component:
    rows = [
        _normal_td(rank),
        _normal_td(dcc.Link(am.cid, href=f'/{Endpoint.AM}/{am.cid}')),
        _normal_td(str(am.nor)),
        _normal_td(am.date_of_signature.strftime('%d/%m/%y')),
        _is_transverse_cell(am.is_transverse),
        _normal_td(_am_descriptor(am)),
        _normal_td(am.source.value),
    ]
    style = {'text-decoration': 'line-through'} if am.state not in (AMState.VIGUEUR, AMState.EN_CREATION) else {}
    return html.Tr(rows, style=style)


def _th(str_: Union[str, Component]) -> Component:
    return html.Th(str_, style={'font-size': '0.85em'})


def _th_with_tooltip(content: str, tooltip_content: str) -> Component:
    id_ = f'tooltip-{tooltip_content}'
    return _th(
        html.Span([dbc.Tooltip(tooltip_content, target=id_), html.Span(content, id=id_, style={'cursor': 'pointer'})])
    )


def _table_header() -> Component:
    return html.Tr(
        [
            _th('#'),
            _th('N° CID'),
            _th('N° NOR'),
            _th('Date'),
            _th_with_tooltip('Tr.', 'Transverse'),
            _th('Classements'),
            _th('Source'),
        ]
    )


def _build_am_table(metadata: Dict[str, AMMetadata], occs: Dict[str, int]) -> Component:
    header = _table_header()
    sorted_ids = sorted(metadata, key=lambda x: (not metadata[x].is_transverse, occs.get(x, 0)), reverse=True)
    rows = [_get_row(rank, metadata[am_id]) for rank, am_id in enumerate(sorted_ids)]
    return html.Table([html.Thead(header), html.Tbody(rows)], className='table table-sm')


def _build_recap(state_counter: Dict[AMState, int]) -> Component:
    deleted = state_counter[AMState.DELETED] + state_counter[AMState.ABROGE]
    txts = [
        f'{state_counter[AMState.VIGUEUR]} arrêté(s) en vigueur',
        f'{state_counter[AMState.EN_CREATION]} arrêté(s) en cours de création',
        f'{deleted} arrêté(s) supprimés',
    ]
    cols = [html.Div(dbc.Card(dbc.CardBody(txt)), className='col-4') for txt in txts]
    return html.Div(cols, className='row mt-4 mb-4')


def _inforced_am_row(id_to_am_metadata: Dict[str, AMMetadata], id_to_occurrences: Dict[str, int]) -> Component:
    id_to_am_metadata = {id_: md for id_, md in id_to_am_metadata.items() if md.state == AMState.VIGUEUR}
    displayed_ids = set(list(id_to_am_metadata))
    id_to_occurrences = {id_: occ for id_, occ in id_to_occurrences.items() if id_ in displayed_ids}
    return html.Div(_build_am_table(id_to_am_metadata, id_to_occurrences))


def _in_creation_am_row(id_to_am_metadata: Dict[str, AMMetadata], id_to_occurrences: Dict[str, int]) -> Component:
    id_to_am_metadata = {id_: md for id_, md in id_to_am_metadata.items() if md.state == AMState.EN_CREATION}
    displayed_ids = set(list(id_to_am_metadata))
    id_to_occurrences = {id_: occ for id_, occ in id_to_occurrences.items() if id_ in displayed_ids}
    return html.Div(_build_am_table(id_to_am_metadata, id_to_occurrences))


def _deleted_am_row(id_to_am_metadata: Dict[str, AMMetadata]) -> Component:
    deleted_am = {
        id_: metadata
        for id_, metadata in id_to_am_metadata.items()
        if metadata.state not in (AMState.VIGUEUR, AMState.EN_CREATION)
    }
    return html.Div(
        [
            html.H3('Arrêtés supprimés ou abrogés.', className='mt-5'),
            html.P('Ces arrêtés ne sont pas exploités dans l\'application envinorma.'),
            _build_am_table(deleted_am, {}),
        ],
    )


def _new_am_button() -> Component:
    return dcc.Link('+ Créer un arrêté', className='btn btn-primary float-end', href=f'/{Endpoint.NEW_AM}')


def _title() -> Component:
    style = {'display': 'inline-block'}
    return html.Div([html.H2('Arrêtés ministériels.', style=style), _new_am_button()])


def _export_alert() -> Component:
    if not get_current_user().is_authenticated:
        return html.Div()
    return dbc.Alert([upload_ams_component()], color='primary')


def _header(state_counter: Dict[AMState, int]) -> Component:
    return html.Div([_title(), html.Hr(), _export_alert(), _build_recap(state_counter)])


def _index_component(id_to_am_metadata: Dict[str, AMMetadata], id_to_occurrences: Dict[str, int]) -> Component:
    states = Counter([md.state for md in id_to_am_metadata.values()])
    sentence = 'Ces arrêtés doivent être déclarés en vigueur une fois les thèmes et le paramétrage définis.'
    return html.Div(
        [
            _header(states),
            html.H3('Arrêtés ministériels en cours de création.', className='mt-2'),
            html.P(sentence),
            _in_creation_am_row(id_to_am_metadata, id_to_occurrences),
            html.H3('Arrêtés ministériels en vigueur.', className='mt-5'),
            _inforced_am_row(id_to_am_metadata, id_to_occurrences),
            _deleted_am_row(id_to_am_metadata),
        ],
        className='container mt-3',
    )


def _layout() -> Component:
    id_to_metadata = DATA_FETCHER.load_all_am_metadata(with_deleted_ams=True)
    return _index_component(id_to_metadata, AM_ID_TO_NB_CLASSEMENTS)


PAGE = Page(_layout, upload_ams_callbacks, False)
