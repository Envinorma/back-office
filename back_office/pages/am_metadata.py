from typing import List, Tuple

import dash_bootstrap_components as dbc
from dash import Dash, dcc, html
from dash.development.base_component import Component
from envinorma.models import AMMetadata, AMState, Classement

from back_office.components import ExtendedComponent, login_redirect
from back_office.components.am_side_nav import page_with_sidebar
from back_office.components.edit_metadata.edit_metadata import edit_metadata
from back_office.helpers.login import get_current_user
from back_office.routing import Endpoint, Page
from back_office.utils import DATA_FETCHER


def _get_str_classement(classement: Classement) -> str:
    if classement.alinea:
        return f'{classement.rubrique}-{classement.regime.value}-al.{classement.alinea}'
    return f'{classement.rubrique}-{classement.regime.value}'


def _get_str_classements(classements: List[Classement]) -> str:
    return ', '.join([_get_str_classement(classement) for classement in classements])


def _row(contents: Tuple[str, ExtendedComponent]) -> Component:
    return html.Tr([html.Td(contents[0], className='font-weight-bold'), html.Td(contents[1])])


def _state(state: AMState) -> Component:
    return dbc.Badge(state.value, color='success' if state == AMState.VIGUEUR else 'danger')


def _metadata(am: AMMetadata) -> Component:
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
    href = f'/{Endpoint.AM}/{am_id}/{Endpoint.AM_METADATA}/edit'
    return dcc.Link(dbc.Button('Modifier les metadonnées', color='primary'), href=href)


def _edition(am_id: str) -> Component:
    return html.Div([html.Div(_edit_metadata_button(am_id), className='float-end')], className='pb-5')


def _layout(am: AMMetadata) -> Component:
    return html.Div([_edition(am.cid), html.Hr(className='mb-4'), _alert(), _metadata(am)])


def _edit_page(am_id: str) -> Component:
    button = dcc.Link(
        html.Button('< Retour aux metadonnées', className='btn btn-link'),
        href=f'/{Endpoint.AM}/{am_id}/{Endpoint.AM_METADATA}',
    )
    return html.Div([button, html.Hr(), html.Div(edit_metadata(False, am_id))])


def _protected_edit(am_id: str) -> Component:
    if get_current_user().is_authenticated:
        return _edit_page(am_id)
    href = f'/{Endpoint.AM}/{am_id}/{Endpoint.AM_METADATA}/edit'
    return login_redirect(href)


def _page(am_id: str, edit: bool = False) -> Component:
    if edit:
        component = _protected_edit(am_id)
    else:
        am = DATA_FETCHER.load_am_metadata(am_id)
        if not am:
            component = html.Div('404 - AM not found')
        else:
            component = _layout(am)
    return page_with_sidebar(component, am_id)


def _add_callbacks(app: Dash) -> None:
    pass


PAGE = Page(_page, _add_callbacks, False)
