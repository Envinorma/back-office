from typing import List, Optional, cast

import dash_bootstrap_components as dbc
from dash import ALL, MATCH, Input, Output, State, callback, dcc, html, no_update
from dash.development.base_component import Component
from envinorma.models import AMMetadata, AMSource, AMState, Classement, Regime
from envinorma.utils import AIDA_URL

from back_office.routing import Endpoint
from back_office.utils import DATA_FETCHER

from . import ids
from .handle_form import handle_form, is_legifrance_id_valid

_REGIME_OPTIONS = [{'label': regime, 'value': regime} for regime in 'AED']
_AM_STATE_OPTIONS = [{'label': el.value, 'value': el.value} for el in AMState]
_AM_SOURCE_OPTIONS = [{'label': el.value, 'value': el.value} for el in AMSource]


def _legifrance_input(am_id: Optional[str]) -> Component:
    return dcc.Input(
        value=am_id or '',
        placeholder='ex: JORFTEXT000012345678',
        id=ids.LEGIFRANCE_ID,
        className='form-control',
        disabled=am_id is not None,
        style={'display': 'flex'},
    )


def _create_button(am_id: Optional[str]) -> Component:
    return html.Button(
        'Créer un nouvel AM', className='btn btn-primary', id=ids.SUBMIT_LEGIFRANCE_ID, hidden=am_id is not None
    )


def _fake_hint(am_id: Optional[str], new_am: bool) -> Component:
    if not new_am or am_id is not None:
        return html.Div()
    return dbc.Alert(
        'Pour créer un AM à des fins de test, choisir un ID commençant par "FAKE".', color='info', className='mt-2'
    )


def _edit_button(am_id: Optional[str], new_am: bool) -> Component:
    text = 'Éditer l\'identifiant Légifrance'
    hidden = not new_am or am_id is None
    return dcc.Link(html.Button(text, className='btn btn-outline-primary', hidden=hidden), href=f'/{Endpoint.NEW_AM}')


def _legifrance_id_form(am_id: Optional[str], new_am: bool) -> Component:
    label = html.Label('Identifiant Légifrance', className='form-label')
    input_ = html.Div(
        [_legifrance_input(am_id), _create_button(am_id), _edit_button(am_id, new_am)], className='input-group'
    )
    return html.Div([label, input_, _fake_hint(am_id, new_am), html.Div(id=ids.SUBMIT_LEGIFRANCE_OUTPUT)])


def _nor_form(am_metadata: Optional[AMMetadata]) -> Component:
    default_value = am_metadata.nor if am_metadata else ''
    return html.Div(
        [
            html.Label('Numéro NOR', className='form-label'),
            dcc.Input(value=default_value, placeholder='ex: DEVP0123456A', id=ids.NOR_ID, className='form-control'),
        ],
        className='mb-3',
        id=ids.NOR_DIV,
    )


def _nor_exists(am_metadata: Optional[AMMetadata]) -> Component:
    default_value = bool(am_metadata.nor) if am_metadata else True
    return html.Div(
        [
            dbc.Checkbox(label='Existence du numéro NOR ?', value=default_value, id=ids.NOR_EXISTS),
            dbc.FormText('Il existe le plus souvent, mais peut ne pas exister pour les vieux arrêtés.'),
        ],
        className='mb-3 mt-3',
    )


def _title(am_metadata: Optional[AMMetadata]) -> Component:
    return html.Div(
        [
            html.Label('Titre', className='form-label'),
            dcc.Textarea(
                value=am_metadata.title if am_metadata else '',
                placeholder='ex: Arrêté du 03/08/18 relatif aux prescriptions générales applicables aux...',
                id=ids.TITLE,
                className='form-control',
            ),
            dbc.FormText('Format attendu : "Arrêté du jj/mm/yy relatif..." ou "Arrêté du jj/mm/yy fixant..."'),
        ],
        className='mb-3',
    )


def _nickname(am_metadata: Optional[AMMetadata]) -> Component:
    default_value = am_metadata.nickname if am_metadata else ''
    return html.Div(
        [
            html.Label('Surnom', className='form-label'),
            dcc.Input(value=default_value, placeholder='Ex: GEREP', id=ids.NICKNAME, className='form-control'),
            dbc.FormText('Peut être laissé vide, est utilisé principalement pour les AM transverses.'),
        ],
        className='mb-3',
    )


def _is_transverse_checkbox(am_metadata: Optional[AMMetadata]) -> Component:
    default_value = am_metadata.is_transverse if am_metadata else False
    return html.Div(
        dbc.Checkbox(value=default_value, id=ids.IS_TRANSVERSE_CHECKBOX, label='AM transverse'), className='mb-3'
    )


def _aida_page_form(am_metadata: Optional[AMMetadata]) -> Component:
    default_value = am_metadata.aida_page if am_metadata else ''
    return html.Div(
        [
            html.Label('Page AIDA', className='form-label'),
            dcc.Input(value=default_value, placeholder='ex: 1234', id=ids.AIDA_PAGE, className='form-control'),
            dbc.FormText(f'Il s\'agit des derniers chiffres de l\'url, par exemple, 1234 pour {AIDA_URL}1234'),
        ],
        className='mb-3',
    )


def _delete_classement_button(rank: int) -> Component:
    return dbc.Button('X', color='light', id=ids.delete_classement_button_id(rank), size='sm', className='ml-1')


def _rubrique_input(rank: int, rubrique: str) -> Component:
    return dcc.Input(
        id=ids.rubrique_input_id(rank),
        value=rubrique or '',
        type='text',
        placeholder='Rubrique (ex: 1234)',
        className='form-control mr-3',
    )


def _regime_dropdown(rank: int, regime: Optional[Regime]) -> Component:
    default = regime.value if regime else None
    return dcc.Dropdown(
        id=ids.regime_id(rank),
        options=_REGIME_OPTIONS,
        clearable=False,
        value=default,
        placeholder='Régime',
        style={'width': '100px'},
    )


def _alinea_input(rank: int, alinea: Optional[str]) -> Component:
    return dcc.Input(
        id=ids.alinea_input_id(rank),
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
    return html.Div(classement_elements, style={'display': 'flex'}, id=ids.classement_row_id(rank), className='mb-3')


def _classements_form(am_metadata: Optional[AMMetadata]) -> Component:
    classements = am_metadata.classements if am_metadata else [None]
    return html.Div(
        [
            html.Label('Classements', className='form-label'),
            html.Div(
                [_classement_row(classement, rank) for rank, classement in enumerate(classements)],
                id=ids.CLASSEMENTS,
            ),
            html.Button('+ nouveau classement', id=ids.ADD_CLASSEMENT_FORM, className='btn btn-secondary btn-sm mt-1'),
        ],
        className='mb-3',
    )


def _am_state(am_metadata: Optional[AMMetadata]) -> Component:
    default_value = am_metadata.state.value if am_metadata else AMState.EN_CREATION.value
    return html.Div(
        [
            html.Label('Statut', className='form-label'),
            dcc.Dropdown(value=default_value, options=_AM_STATE_OPTIONS, id=ids.AM_STATE, placeholder='Statut'),
            dbc.FormText(
                'Choisir EN_CREATION tant que l\'AM n\'est pas prêt à être exploité. '
                'Choisir VIGUEUR pour que l\'AM soit exploité dans Envinorma. '
                'Il est possible de créer un arrêté abrogé ou supprimé principalement à des fins de test. '
                'Une fois créé, un AM n\'est jamais supprimé pour permettre une restauration éventuelle. '
                'La suppression est indiquée par le statut DELETED. '
                'Le statut ABROGE est réservé pour un AM qui a été en vigueur dans le passé.'
            ),
        ],
        className='mb-3',
    )


def _am_source(am_metadata: Optional[AMMetadata]) -> Component:
    default_value = am_metadata.source.value if am_metadata else None
    return html.Div(
        [
            html.Label('Source', className='form-label'),
            dcc.Dropdown(value=default_value, options=_AM_SOURCE_OPTIONS, id=ids.AM_SOURCE, placeholder='Source'),
            dbc.FormText(
                'La source qui sera utilisée pour initialiser l\'arrêté. Choisir Légifrance '
                'par défaut, sauf si il manque les annexes ou une autre partie du texte sur Légifrance, ou si la '
                'version consolidée n\'existe pas.'
            ),
        ],
        className='mb-3',
    )


def _reason_deleted(am_metadata: Optional[AMMetadata]) -> Component:
    default_value = am_metadata.reason_deleted if am_metadata else None
    return html.Div(
        [
            html.Label('Raison de suppression ', className='form-label'),
            dbc.Input(value=default_value, type='text', id=ids.REASON_DELETED),
            dbc.FormText('À ne renseigner que si le statut choisi est DELETED.'),
        ],
        className='mb-3',
        hidden=False,
        id=ids.REASON_DELETED_DIV,
    )


def _warning(am_metadata: Optional[AMMetadata]) -> Component:
    if not am_metadata:
        return html.Div()
    return dbc.Alert(
        'Cet arrêté existe déjà. L\'opération engendrera une modification de celui-ci.',
        color='warning',
        className='mt-2',
    )


def _submit_button() -> Component:
    return html.Button('Valider', className='btn btn-primary mb-5', id=ids.SUBMIT_BUTTON)


def _metadata_form(am_metadata: Optional[AMMetadata]) -> Component:
    return html.Div(
        [
            _warning(am_metadata),
            _nor_exists(am_metadata),
            _nor_form(am_metadata),
            _title(am_metadata),
            _nickname(am_metadata),
            _is_transverse_checkbox(am_metadata),
            _aida_page_form(am_metadata),
            _classements_form(am_metadata),
            _am_state(am_metadata),
            _reason_deleted(am_metadata),
            _am_source(am_metadata),
            dbc.Spinner(html.Div(), id=ids.FORM_OUTPUT),
            _submit_button(),
        ]
    )


def _metadata_row(am_id: Optional[str], metadata: Optional[AMMetadata]) -> Component:
    if not am_id:
        return html.Div()
    return _metadata_form(metadata)


def _form(am_id: Optional[str], metadata: Optional[AMMetadata], new_am: bool) -> Component:
    return html.Div(
        [_legifrance_id_form(am_id, new_am), _metadata_row(am_id, metadata), dcc.Store(data=am_id, id=ids.AM_ID)]
    )


@callback(Output(ids.REASON_DELETED_DIV, 'hidden'), Input(ids.AM_STATE, 'value'))
def set_reason_deleted_visibility(am_state: Optional[str]) -> bool:
    return am_state != AMState.DELETED.value


@callback(Output(ids.NOR_DIV, 'hidden'), Input(ids.NOR_EXISTS, 'value'))
def set_nor_visibility(checked) -> bool:
    return not checked


@callback(Output(ids.REASON_DELETED, 'value'), Input(ids.AM_STATE, 'value'))
def clear_reason_deleted(am_state: Optional[str]):
    if am_state != AMState.DELETED.value:
        return ''
    return no_update


@callback(
    Output(ids.SUBMIT_LEGIFRANCE_OUTPUT, 'children'),
    Input(ids.SUBMIT_LEGIFRANCE_ID, 'n_clicks'),
    State(ids.LEGIFRANCE_ID, 'value'),
    prevent_initial_call=True,
)
def refresh_page(_, legifrance_id: Optional[str]) -> Component:
    legifrance_id = legifrance_id or ''
    if not is_legifrance_id_valid(legifrance_id):
        return dbc.Alert(
            'L\'identifiant Legifrance est invalide : il doit contenir 20 caractères.',
            color='danger',
            className='mt-2 mb-3',
            dismissable=True,
        )
    return dcc.Location(pathname=f'/{Endpoint.NEW_AM}/{legifrance_id}', id=ids.REFRESH_REDIRECT)


@callback(
    Output(ids.classement_row_id(cast(int, MATCH)), 'children'),
    Input(ids.delete_classement_button_id(cast(int, MATCH)), 'n_clicks'),
    prevent_initial_call=True,
)
def delete_section(_):
    return html.Div()


@callback(
    Output(ids.CLASSEMENTS, 'children'),
    Input(ids.ADD_CLASSEMENT_FORM, 'n_clicks'),
    State(ids.CLASSEMENTS, 'children'),
    State(ids.classement_row_id(cast(int, ALL)), 'id'),
    prevent_initial_call=True,
)
def add_block(_, children, ids):
    new_rank = (max([cast(int, id_['rank']) for id_ in ids]) + 1) if ids else 0
    new_block = _classement_row(None, rank=new_rank)
    return children + [new_block]


@callback(
    Output(ids.FORM_OUTPUT, 'children'),
    Input(ids.SUBMIT_BUTTON, 'n_clicks'),
    State(ids.AM_ID, 'data'),
    State(ids.TITLE, 'value'),
    State(ids.NICKNAME, 'value'),
    State(ids.IS_TRANSVERSE_CHECKBOX, 'value'),
    State(ids.AIDA_PAGE, 'value'),
    State(ids.AM_STATE, 'value'),
    State(ids.AM_SOURCE, 'value'),
    State(ids.NOR_EXISTS, 'value'),
    State(ids.NOR_ID, 'value'),
    State(ids.REASON_DELETED, 'value'),
    State(ids.rubrique_input_id(cast(int, ALL)), 'value'),
    State(ids.regime_id(cast(int, ALL)), 'value'),
    State(ids.alinea_input_id(cast(int, ALL)), 'value'),
    prevent_initial_call=True,
)
def _handle_form(
    _,
    am_id: Optional[str],
    title: Optional[str],
    nickname: Optional[str],
    is_transverse: bool,
    aida_page: Optional[str],
    am_state: Optional[str],
    am_source: Optional[str],
    nor_exists: bool,
    nor_id: Optional[str],
    reason_deleted: Optional[str],
    rubriques: List[Optional[str]],
    regimes: List[Optional[str]],
    alineas: List[Optional[str]],
):

    return handle_form(
        am_id,
        title,
        nickname,
        is_transverse,
        aida_page,
        am_state,
        am_source,
        nor_exists,
        nor_id,
        reason_deleted,
        rubriques,
        regimes,
        alineas,
    )


def edit_metadata(new_am: bool, am_id: Optional[str] = None) -> Component:
    metadata = DATA_FETCHER.load_am_metadata(am_id) if am_id else None
    title = 'Nouvel arrêté ministériel.' if new_am else f"Modification de l'arrêté ministériel {am_id}."
    return html.Div([html.H3(title), _form(am_id, metadata, new_am)])
