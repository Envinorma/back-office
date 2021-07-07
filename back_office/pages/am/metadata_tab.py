from typing import List, Tuple

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash import Dash
from dash.development.base_component import Component
from envinorma.models import AMMetadata, AMState, Classement
from envinorma.utils import AMStatus

from back_office.helpers.login import get_current_user
from back_office.routing import Endpoint
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


def _edition(am_id: str) -> Component:
    alert = (
        dbc.Alert('Cet arrêté peut être modifié, restructuré ou paramétré par toute personne.')
        if not get_current_user().is_authenticated
        else html.Div()
    )
    delete_button = dcc.Link(dbc.Button('Supprimer l\'arrêté', color='danger'), href=f'/{Endpoint.DELETE_AM}/{am_id}')
    return html.Div(
        [
            html.H2('Éditer'),
            alert,
            html.Div(dcc.Link(dbc.Button('Éditer le contenu de l\'arrêté', color='success'), href=f'/edit_am/{am_id}')),
            html.Div(delete_button, className='mt-2'),
        ]
    )


def _layout(am: AMMetadata) -> Component:
    return html.Div(
        [
            html.Div(className='row', children=_metadata(am)),
            html.Div(className='row', children=_edition(am.cid)),
        ]
    )


def _callbacks(app: Dash, tab_id: str) -> None:
    ...


TAB = ('Metadonnées', _layout, _callbacks)
