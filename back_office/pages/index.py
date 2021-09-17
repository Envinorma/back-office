from collections import Counter
from typing import Dict, Union

import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.development.base_component import Component
from envinorma.models import AMMetadata, AMState, Classement

from back_office.components import replace_line_breaks
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


def _get_row(rank: int, am: AMMetadata, occurrences: int) -> Component:
    rows = [
        _normal_td(rank),
        _normal_td(dcc.Link(am.cid, href=f'/{Endpoint.AM}/{am.cid}')),
        _normal_td(str(am.nor)),
        _normal_td(am.date_of_signature.strftime('%d/%m/%y')),
        _is_transverse_cell(am.is_transverse),
        _normal_td(_am_descriptor(am)),
        _normal_td(am.source.value),
        _normal_td(occurrences),
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


def _get_header() -> Component:
    return html.Tr(
        [
            _th('#'),
            _th('N° CID'),
            _th('N° NOR'),
            _th('Date'),
            _th_with_tooltip('Tr.', 'Transverse'),
            _th('Classements'),
            _th('Source'),
            _th('Occs.'),
        ]
    )


def _build_am_table(metadata: Dict[str, AMMetadata], occs: Dict[str, int]) -> Component:
    header = _get_header()
    sorted_ids = sorted(metadata, key=lambda x: (not metadata[x].is_transverse, occs.get(x, 0)), reverse=True)
    rows = [_get_row(rank, metadata[am_id], occs.get(am_id, 0)) for rank, am_id in enumerate(sorted_ids)]
    return html.Table([html.Thead(header), html.Tbody(rows)], className='table table-sm')


def _build_recap(state_counter: Dict[AMState, int]) -> Component:
    txts = [
        f'{state_counter[AMState.VIGUEUR]} arrêté(s) en vigueur\n',
        f'{state_counter[AMState.EN_CREATION]} arrêté(s) en cours de création',
    ]
    cols = [
        html.Div(
            html.Div(html.Div(replace_line_breaks(txt), className='card-body'), className='card text-center'),
            className='col-3',
        )
        for txt in txts
    ]
    return html.Div(cols, className='row', style={'margin-top': '20px'})


def _add_am_button() -> Component:
    return html.Div(
        dcc.Link(html.Button('+ Créer un arrêté', className='btn btn-link'), href=f'/{Endpoint.CREATE_AM}'),
        style={'text-align': 'right'},
    )


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


def _index_component(id_to_am_metadata: Dict[str, AMMetadata], id_to_occurrences: Dict[str, int]) -> Component:
    states = Counter([md.state for md in id_to_am_metadata.values()])
    sentence = 'Ces arrêtés doivent être déclarés en vigueur une fois les thèmes et le paramétrage définis.'
    return html.Div(
        [
            html.H2('Arrêtés ministériels.'),
            _build_recap(states),
            _add_am_button(),
            html.H3('Arrêtés ministériels en cours de création.', className='mt-2'),
            html.P(sentence),
            _in_creation_am_row(id_to_am_metadata, id_to_occurrences),
            html.H3('Arrêtés ministériels en vigueur.', className='mt-5'),
            _inforced_am_row(id_to_am_metadata, id_to_occurrences),
            _deleted_am_row(id_to_am_metadata),
        ]
    )


def _layout() -> Component:
    id_to_metadata = DATA_FETCHER.load_all_am_metadata(with_deleted_ams=True)
    return _index_component(id_to_metadata, AM_ID_TO_NB_CLASSEMENTS)


PAGE = Page(_layout, None, False)
