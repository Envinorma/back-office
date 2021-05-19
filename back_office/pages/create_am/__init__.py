from typing import Any, Dict, List, Optional, cast

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import ALL, Input, MATCH, Output, State
from dash.development.base_component import Component
from envinorma.data import AMMetadata, AMSource, AMState, Classement, Regime
from envinorma.utils import AIDA_URL

from back_office.routing import Endpoint, Page
from back_office.utils import DATA_FETCHER, get_current_user

from . import create_am_ids as page_ids
from .am_creation_form_handling import handle_form, is_legifrance_id_valid

_REGIME_OPTIONS = [{'label': regime.value, 'value': regime.value} for regime in Regime]
_AM_STATE_OPTIONS = [{'label': el.value, 'value': el.value} for el in AMState]
_AM_SOURCE_OPTIONS = [{'label': el.value, 'value': el.value} for el in AMSource]


def _legifrance_id_form(am_id: Optional[str]) -> Component:
    input_ = html.Div(
        [
            dcc.Input(
                value=am_id or '',
                placeholder='ex: JORFTEXT000012345678',
                id=page_ids.LEGIFRANCE_ID,
                className='form-control',
                disabled=am_id is not None,
                style={'display': 'flex'},
            ),
            html.Button(
                'Créer l\'AM', className='btn btn-primary', id=page_ids.SUBMIT_LEGIFRANCE_ID, hidden=am_id is not None
            ),
            dcc.Link(
                html.Button('Éditer', className='btn btn-outline-primary', hidden=am_id is None),
                href=f'/{Endpoint.CREATE_AM}',
            ),
        ],
        className='input-group',
    )
    return dbc.FormGroup(
        [
            html.Label(f'Identifiant Légifrance', className='form-label'),
            input_,
            html.Div(id=page_ids.SUBMIT_LEGIFRANCE_OUTPUT),
        ]
    )


def _nor_form(am_metadata: Optional[AMMetadata]) -> Component:
    return dbc.FormGroup(
        [
            html.Label(f'Numéro NOR', className='form-label'),
            dcc.Input(
                value=am_metadata.nor if am_metadata else '',
                placeholder='ex: DEVP0123456A',
                id=page_ids.NOR_ID,
                className='form-control',
            ),
        ]
    )


def _title(am_metadata: Optional[AMMetadata]) -> Component:
    return dbc.FormGroup(
        [
            html.Label(f'Titre', className='form-label'),
            dcc.Textarea(
                value=am_metadata.title if am_metadata else '',
                placeholder='ex: Arrêté du 03/08/18 relatif aux prescriptions générales applicables aux...',
                id=page_ids.TITLE,
                className='form-control',
            ),
            dbc.FormText('Format attendu : "Arrêté du jj/mm/yy relatif..." ou "Arrêté du jj/mm/yy fixant..."'),
        ]
    )


def _aida_page_form(am_metadata: Optional[AMMetadata]) -> Component:
    default_value = am_metadata.aida_page if am_metadata else ''
    return dbc.FormGroup(
        [
            html.Label(
                f'Page AIDA',
                className='form-label',
            ),
            dcc.Input(value=default_value, placeholder='ex: 1234', id=page_ids.AIDA_PAGE, className='form-control'),
            dbc.FormText(f'Il s\'agit des derniers chiffres de l\'url, par exemple, 1234 pour {AIDA_URL}1234'),
        ]
    )


def _delete_classement_button(rank: int) -> Component:
    return dbc.Button('X', color='light', id=page_ids.delete_classement_button_id(rank), size='sm', className='ml-1')


def _rubrique_input(rank: int, rubrique: str) -> Component:
    return dcc.Input(
        id=page_ids.rubrique_input_id(rank),
        value=rubrique or '',
        type='text',
        placeholder='Rubrique (ex: 1234)',
        className='form-control mr-3',
    )


def _regime_dropdown(rank: int, regime: Optional[Regime]) -> Component:
    default = regime.value if regime else None
    return dcc.Dropdown(
        id=page_ids.regime_id(rank),
        options=_REGIME_OPTIONS,
        clearable=False,
        value=default,
        placeholder='Régime',
        style={'width': '100px'},
    )


def _alinea_input(rank: int, alinea: Optional[str]) -> Component:
    return dcc.Input(
        id=page_ids.alinea_input_id(rank),
        value=alinea or '',
        type='text',
        placeholder='Alinéa (ex: A.3)',
        className='form-control ml-3',
    )


def _classement_row(classement: Optional[Classement], rank: int) -> Component:
    classement_elements = [
        _rubrique_input(rank, classement.rubrique if classement else ''),
        _regime_dropdown(rank, classement.regime if classement else None),
        _alinea_input(rank, classement.alinea if classement else None),
        _delete_classement_button(rank),
    ]
    return dbc.FormGroup(classement_elements, style={'display': 'flex'}, id=page_ids.classement_row_id(rank))


def _classements_form(am_metadata: Optional[AMMetadata]) -> Component:
    classements = am_metadata.classements if am_metadata else [None]
    return dbc.FormGroup(
        [
            html.Label(f'Classements', className='form-label'),
            html.Div(
                [_classement_row(classement, rank) for rank, classement in enumerate(classements)],
                id=page_ids.CLASSEMENTS,
            ),
            html.Button(
                '+ nouveau classement', id=page_ids.ADD_CLASSEMENT_FORM, className='btn btn-secondary btn-sm mt-1'
            ),
        ]
    )


def _am_state(am_metadata: Optional[AMMetadata]) -> Component:
    default_value = am_metadata.state.value if am_metadata else None
    return dbc.FormGroup(
        [
            html.Label(f'Statut', className='form-label'),
            dcc.Dropdown(value=default_value, options=_AM_STATE_OPTIONS, id=page_ids.AM_STATE, placeholder='Statut'),
        ]
    )


def _publication_date(am_metadata: Optional[AMMetadata]) -> Component:
    default_value = am_metadata.publication_date if am_metadata else None
    return dbc.FormGroup(
        [
            html.Label(f'Date de publication', className='form-label'),
            dbc.Input(value=default_value, type='date', id=page_ids.PUBLICATION_DATE),
        ]
    )


def _am_source(am_metadata: Optional[AMMetadata]) -> Component:
    default_value = am_metadata.source.value if am_metadata else None
    return dbc.FormGroup(
        [
            html.Label(f'Source', className='form-label'),
            dcc.Dropdown(value=default_value, options=_AM_SOURCE_OPTIONS, id=page_ids.AM_SOURCE, placeholder='Source'),
            dbc.FormText(
                'La source qui sera utilisée pour initialiser l\'arrêté. Choisir Légifrance '
                'par défaut, sauf si il manque les annexes ou une autre partie du texte sur Légifrance.'
            ),
        ]
    )


def _reason_deleted(am_metadata: Optional[AMMetadata]) -> Component:
    default_value = am_metadata.reason_deleted if am_metadata else None
    return dbc.FormGroup(
        [
            html.Label(f'Raison de suppression ', className='form-label'),
            dbc.Input(value=default_value, type='text', id=page_ids.REASON_DELETED),
            dbc.FormText('À ne renseigner que si le statut choisi est "deleted".'),
        ]
    )


def _warning(am_metadata: Optional[AMMetadata]) -> Component:
    if not am_metadata:
        return html.Div()
    return dbc.Alert('Cet arrêté existe déjà. L\'opération engendrera une modification de celui-ci.', color='warning')


def _submit_button() -> Component:
    return html.Button('Valider', className='btn btn-primary mb-5', id=page_ids.SUBMIT_BUTTON)


def _metadata_form(am_metadata: Optional[AMMetadata]) -> Component:
    return html.Div(
        [
            _warning(am_metadata),
            _nor_form(am_metadata),
            _title(am_metadata),
            _aida_page_form(am_metadata),
            _classements_form(am_metadata),
            _am_state(am_metadata),
            _publication_date(am_metadata),
            _am_source(am_metadata),
            _reason_deleted(am_metadata),
            html.Div(id=page_ids.FORM_OUTPUT),
            _submit_button(),
        ]
    )


def _metadata_row(am_id: Optional[str]) -> Component:
    if not am_id:
        return html.Div()
    return _metadata_form(DATA_FETCHER.load_am_metadata(am_id))


def _form(am_id: Optional[str]) -> Component:
    return html.Div(
        [
            _legifrance_id_form(am_id),
            _metadata_row(am_id),
            dcc.Store(data=am_id, id=page_ids.AM_ID),
        ]
    )


def _page_if_logged(am_id: Optional[str]) -> Component:
    return html.Div([html.H2(f'Nouvel arrêté ministériel.'), _form(am_id)])


def _page(am_id: Optional[str] = None) -> Component:
    if not get_current_user().is_authenticated:
        return dcc.Location(pathname='/login', id='login-redirect')
    return _page_if_logged(am_id)


def _add_callbacks(app: dash.Dash) -> None:
    @app.callback(
        Output(page_ids.SUBMIT_LEGIFRANCE_OUTPUT, 'children'),
        Input(page_ids.SUBMIT_LEGIFRANCE_ID, 'n_clicks'),
        State(page_ids.LEGIFRANCE_ID, 'value'),
        prevent_initial_call=True,
    )
    def refresh_page(_, legifrance_id: Optional[str]) -> Component:
        legifrance_id = legifrance_id or ''
        if not is_legifrance_id_valid(legifrance_id):
            return dbc.Alert(
                'L\'identifiant Legifrance est invalide : il doit contenir 20 caractères.',
                color='danger',
                className='mt-2 mb-2',
                dismissable=True,
            )
        return dcc.Location(pathname=f'/{Endpoint.CREATE_AM}/{legifrance_id}', id=page_ids.REFRESH_REDIRECT)

    @app.callback(
        Output(page_ids.classement_row_id(cast(int, MATCH)), 'children'),
        Input(page_ids.delete_classement_button_id(cast(int, MATCH)), 'n_clicks'),
        prevent_initial_call=True,
    )
    def delete_section(_):
        return html.Div()

    @app.callback(
        Output(page_ids.CLASSEMENTS, 'children'),
        Input(page_ids.ADD_CLASSEMENT_FORM, 'n_clicks'),
        State(page_ids.CLASSEMENTS, 'children'),
        State(page_ids.classement_row_id(cast(int, ALL)), 'id'),
        prevent_initial_call=True,
    )
    def add_block(_, children, ids):
        new_rank = (max([cast(int, id_['rank']) for id_ in ids]) + 1) if ids else 0
        new_block = _classement_row(None, rank=new_rank)
        return children + [new_block]

    @app.callback(
        Output(page_ids.FORM_OUTPUT, 'children'),
        Input(page_ids.SUBMIT_BUTTON, 'n_clicks'),
        State(page_ids.AM_ID, 'data'),
        State(page_ids.TITLE, 'value'),
        State(page_ids.AIDA_PAGE, 'value'),
        State(page_ids.AM_STATE, 'value'),
        State(page_ids.PUBLICATION_DATE, 'value'),
        State(page_ids.AM_SOURCE, 'value'),
        State(page_ids.NOR_ID, 'value'),
        State(page_ids.REASON_DELETED, 'value'),
        State(page_ids.rubrique_input_id(cast(int, ALL)), 'value'),
        State(page_ids.regime_id(cast(int, ALL)), 'value'),
        State(page_ids.alinea_input_id(cast(int, ALL)), 'value'),
        prevent_initial_call=True,
    )
    def _handle_form(
        _,
        am_id: Optional[str],
        title: Optional[str],
        aida_page: Optional[str],
        am_state: Optional[str],
        publication_date: Optional[str],
        am_source: Optional[str],
        nor_id: Optional[str],
        reason_deleted: Optional[str],
        rubriques: List[Optional[str]],
        regimes: List[Optional[str]],
        alineas: List[Optional[str]],
    ):

        return handle_form(
            am_id,
            title,
            aida_page,
            am_state,
            publication_date,
            am_source,
            nor_id,
            reason_deleted,
            rubriques,
            regimes,
            alineas,
        )


PAGE = Page(_page, _add_callbacks)
