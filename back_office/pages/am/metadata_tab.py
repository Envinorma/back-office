from typing import List, Tuple

import dash_html_components as html
from dash import Dash
from dash.development.base_component import Component
from envinorma.models import AMMetadata, AMState, Classement
from envinorma.utils import AMStatus

from back_office.utils import DATA_FETCHER


def _get_str_classement(classement: Classement) -> str:
    if classement.alinea:
        return f'{classement.rubrique}-{classement.regime.value}-al.{classement.alinea}'
    return f'{classement.rubrique}-{classement.regime.value}'


def _get_str_classements(classements: List[Classement]) -> str:
    return ', '.join([_get_str_classement(classement) for classement in classements])


def _row(contents: Tuple[str, str], second_class_name: str) -> Component:
    return html.Tr(
        [html.Td(contents[0], className='font-weight-bold'), html.Td(contents[1], className=second_class_name)]
    )


def _metadata(am: AMMetadata) -> Component:
    date_ = am.date_of_signature.strftime('%d/%m/%y')
    status = DATA_FETCHER.load_am_status(am.cid)
    return html.Table(
        [
            _row(('Id', am.cid), ''),
            _row(('Titre', am.title), ''),
            _row(('Date de signature', date_), ''),
            _row(('NOR', am.nor or ''), ''),
            _row(('Initialisé via', am.source.value), ''),
            _row(('État', am.state.value), 'table-success' if am.state == AMState.VIGUEUR else 'table-danger'),
            _row(('Statut', status.value), 'table-success' if status == AMStatus.VALIDATED else 'table-danger'),
            _row(('Classements', _get_str_classements(am.classements)), ''),
        ],
        className='table table-bordered',
    )


def _layout(am: AMMetadata) -> Component:
    return html.Div(
        [
            html.H4('Métadonnées', className='row, mb-3'),
            html.Div(className='row', children=_metadata(am)),
        ]
    )


def _callbacks(app: Dash) -> None:
    ...


TAB = ('Metadonnées', _layout, _callbacks)
