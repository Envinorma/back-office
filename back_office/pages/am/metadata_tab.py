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


def _row(contents: Tuple[str, str]) -> Component:
    return html.Tr([html.Td(contents[0], className='font-weight-bold'), html.Td(contents[1])])


def _state(state: AMState) -> Component:
    return dbc.Badge(state.value, color='success' if state == AMState.VIGUEUR else 'danger')


def _status(status: AMStatus) -> Component:
    return dbc.Badge(status.value, color='success' if status == AMStatus.VALIDATED else 'danger')


def _metadata(am: AMMetadata, status: AMStatus) -> Component:
    date_ = am.date_of_signature.strftime('%d/%m/%y')
    return html.Table(
        [
            _row(('Id', am.cid)),
            _row(('Titre', am.title)),
            _row(('Date de signature', date_)),
            _row(('Surnom', am.nickname or '')),
            _row(('Transverse', 'OUI' if am.is_transverse else 'NON')),
            _row(('NOR', am.nor or '')),
            _row(('Initialisé via', am.source.value)),
            _row(('État', _state(am.state))),
            _row(('Statut', _status(status))),
            _row(('Classements', _get_str_classements(am.classements))),
        ],
        className='table table-bordered',
    )


def _alert() -> Component:
    return (
        dbc.Alert(
            'Toute suggestion de modification est bienvenue. Vous pouvez en faire part '
            "par email à l'adresse drieat-if.envinorma@developpement-durable.gouv.fr",
            color='primary',
        )
        if not get_current_user().is_authenticated
        else html.Div()
    )


def _edit_metadata_button(am_id: str) -> Component:
    return dcc.Link(dbc.Button('Modifier les metadonnées', color='primary'), href=f'/{Endpoint.CREATE_AM}/{am_id}')


def _edit_content_button(am_id: str) -> Component:
    return dcc.Link(
        dbc.Button("Modifier le contenu de l'arrêté", color='primary'), href=f'/{Endpoint.EDIT_AM_CONTENT}/{am_id}'
    )


def _reinit_button(am_id: str, am_status: AMStatus) -> Component:
    button_wording = "Initialiser l'arrêté" if am_status == AMStatus.PENDING_INITIALIZATION else 'Éditer le paramétrage'
    return dcc.Link(dbc.Button(button_wording, color='primary'), href=f'/edit_am/{am_id}')


def _delete_button(am_id: str) -> Component:
    return dcc.Link(dbc.Button("Supprimer l'arrêté", color='danger'), href=f'/{Endpoint.DELETE_AM}/{am_id}')


def _edition(am_id: str, am_status: AMStatus) -> Component:
    return html.Div(
        [
            html.H3('Édition'),
            _alert(),
            html.Div(_edit_metadata_button(am_id), className='pb-2'),
            html.Div(_edit_content_button(am_id), className='pb-2'),
            html.Div(_reinit_button(am_id, am_status), className='pb-2'),
            html.Div(_delete_button(am_id), className='pb-2'),
        ],
        style={'background-color': '#EEEEEE', 'border-radius': '5px'},
        className='p-3',
    )


def _layout(am: AMMetadata) -> Component:
    status = DATA_FETCHER.load_am_status(am.cid)
    return html.Div(
        [
            html.Div(className='col-8', children=_metadata(am, status)),
            html.Div(className='col-4', children=_edition(am.cid, status)),
        ],
        className='row',
    )


def _callbacks(app: Dash, tab_id: str) -> None:
    ...


TAB = ('Metadonnées', _layout, _callbacks)
