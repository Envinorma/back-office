import traceback
import warnings
from typing import Any, Dict, List, Optional, Tuple, Union

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import MATCH, Input, Output, State
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
from envinorma.io.markdown import extract_markdown_text
from envinorma.models import AMMetadata, ArreteMinisteriel, Ints
from envinorma.parametrization import AlternativeSection, AMWarning, InapplicableSection, Parametrization
from envinorma.parametrization.resync import UndefinedTitlesSequencesError, add_titles_sequences, regenerate_paths
from envinorma.topics.simple_topics import add_simple_topics
from envinorma.utils import AMStatus

from back_office.app_init import app
from back_office.components import ButtonState, button, error_component, link_button
from back_office.components.am_component import am_component
from back_office.components.parametric_am_list import parametric_am_list_callbacks
from back_office.components.summary_component import summary_component
from back_office.components.table import ExtendedComponent, table_component
from back_office.config import ENVIRONMENT_TYPE, EnvironmentType
from back_office.helpers.slack import SlackChannel, send_slack_notification
from back_office.helpers.texts import get_traversed_titles, safe_get_section
from back_office.pages.edit_am.am_init_edition import router as am_init_router
from back_office.pages.edit_am.am_init_tab import am_init_tab
from back_office.pages.edit_am.structure_edition import router as structure_router
from back_office.pages.parametrization_edition import router as parametrization_router
from back_office.routing import Endpoint
from back_office.utils import DATA_FETCHER, AMOperation

_PREFIX = __file__.split('/')[-1].replace('.py', '').replace('_', '-')
_VALIDATE_INITIALIZATION = f'{_PREFIX}-validate-init'
_VALIDATE_STRUCTURE = f'{_PREFIX}-validate-structure'
_VALIDATE_PARAMETRIZATION = f'{_PREFIX}-validate-parametrization'
_LOADER = f'{_PREFIX}-loading-output'


def _modal_confirm_button_id(step: Optional[str] = None) -> Dict[str, Any]:
    return {'type': f'{_PREFIX}-modal-confirm-button', 'step': step or MATCH}


def _close_modal_button_id(step: Optional[str] = None) -> Dict[str, Any]:
    return {'type': f'{_PREFIX}-close-modal-button', 'step': step or MATCH}


def _modal_id(step: Optional[str] = None) -> Dict[str, Any]:
    return {'type': f'{_PREFIX}-modal', 'step': step or MATCH}


def _modal_button_id(step: Optional[str] = None) -> Dict[str, Any]:
    return {'type': f'{_PREFIX}-modal-button', 'step': step or MATCH}


def _extract_am_id_and_operation(pathname: str) -> Tuple[str, Optional[AMOperation], str]:
    pieces = pathname.split('/')[1:]
    if len(pieces) == 0:
        raise ValueError('Unexpected')
    if len(pieces) == 1:
        return pieces[0], None, ''
    return pieces[0], AMOperation(pieces[1]), '/'.join(pieces[2:])


def _get_edit_structure_button(parent_page: str) -> Component:
    href = f'{parent_page}/{AMOperation.EDIT_STRUCTURE.value}'
    return link_button('Éditer la structure', href, state=ButtonState.NORMAL_LINK)


def _am_initialization_buttons() -> Tuple[Optional[Component], Optional[Component]]:
    return (None, button('Valider le texte initial', id_=_VALIDATE_INITIALIZATION, state=ButtonState.NORMAL))


def _get_confirmation_modal(
    button_text: str, modal_body: Union[str, Component], step: str, className: str
) -> Component:
    modal = dbc.Modal(
        [
            dbc.ModalHeader('Confirmation'),
            dbc.ModalBody(modal_body),
            dbc.ModalFooter(
                [
                    html.Button('Annuler', id=_close_modal_button_id(step), className='btn btn-light'),
                    html.Button('Confirmer', id=_modal_confirm_button_id(step), className='ml-auto btn btn-danger'),
                ]
            ),
        ],
        id=_modal_id(step),
    )
    return html.Div(
        [html.Button(button_text, id=_modal_button_id(step), className=className), modal],
        style={'display': 'inline-block'},
    )


def _get_reset_structure_button() -> Component:
    modal_content = 'Êtes-vous sûr de vouloir réinitialiser le texte ? Cette opération est irréversible.'
    return _get_confirmation_modal('Réinitialiser le texte', modal_content, 'reset-structure', 'btn btn-danger')


def _structure_validation_buttons(parent_page: str) -> Tuple[Optional[Component], Optional[Component]]:
    modal_content = (
        'Êtes-vous sûr de vouloir retourner à la phase d\'initialisation du texte ? Ceci est '
        'déconseillé lorsque l\'AM provient de Légifrance ou que la structure a déjà été modifiée.'
    )
    validate_button = button('Valider la structure', id_=_VALIDATE_STRUCTURE, state=ButtonState.NORMAL)
    right_buttons = html.Div(
        [_get_reset_structure_button(), ' ', _get_edit_structure_button(parent_page), ' ', validate_button],
        style={'display': 'inline-block'},
    )
    return (
        _get_confirmation_modal('Étape précédente', modal_content, 'structure', 'btn btn-light'),
        right_buttons,
    )


def _parametrization_edition_buttons() -> Tuple[Optional[Component], Optional[Component]]:
    modal_content = (
        'Êtes-vous sûr de vouloir retourner à la phase de structuration du texte ? Si des paramètres '
        'ont déjà été renseignés, cela peut désaligner certains paramétrages.'
    )
    return (
        _get_confirmation_modal('Étape précédente', modal_content, 'parametrization', 'btn btn-light'),
        button('Valider le paramétrage', id_=_VALIDATE_PARAMETRIZATION, state=ButtonState.NORMAL),
    )


def _inline_buttons(button_left: Optional[Component], button_right: Optional[Component]) -> List[Component]:
    left = html.Div(button_left, style={'display': 'inline-block', 'float': 'left'})
    right = html.Div(button_right, style={'display': 'inline-block', 'float': 'right'})
    return [left, right]


def _get_buttons(am_status: AMStatus, parent_page: str) -> Component:
    successive_buttons = [
        _am_initialization_buttons(),
        _structure_validation_buttons(parent_page),
        _parametrization_edition_buttons(),
    ]
    visibility = [am_status.step() == 0, am_status.step() == 1, am_status.step() >= 2]
    style = {
        'position': 'fixed',
        'bottom': '0px',
        'left': '0px',
        'width': '100%',
        'background-color': 'white',
        'padding-bottom': '10px',
        'padding-top': '10px',
    }
    return html.Div(
        [
            html.Div(html.Div(_inline_buttons(*buttons), className='container'), hidden=not visible, style=style)
            for buttons, visible in zip(successive_buttons, visibility)
        ]
    )


def _human_alinea_tuple(ints: Optional[List[int]]) -> str:
    if not ints:
        return 'Tous'
    return ', '.join(map(str, sorted(ints)))


def _application_condition_to_row(
    inapplicable_section: InapplicableSection, am: ArreteMinisteriel, rank: int, current_page: str
) -> List[ExtendedComponent]:
    target_section = inapplicable_section.targeted_entity.section
    reference_str = _get_section_title_or_error(target_section.path, am, target_section.titles_sequence)
    alineas = _human_alinea_tuple(inapplicable_section.targeted_entity.outer_alinea_indices)
    condition = _small(inapplicable_section.condition.to_str())
    source_section = inapplicable_section.source.reference.section
    source = _get_section_title_or_error(source_section.path, am, source_section.titles_sequence)
    href = f'{current_page}/{AMOperation.ADD_CONDITION.value}/{rank}'
    edit = link_button('Éditer', href=href, state=ButtonState.NORMAL_LINK)
    href_copy = f'{current_page}/{AMOperation.ADD_CONDITION.value}/{rank}/copy'
    copy = link_button('Copier', href=href_copy, state=ButtonState.NORMAL_LINK)
    return [str(rank), reference_str, alineas, condition, source, edit, copy]


def _get_inapplicable_sections_table(
    parametrization: Parametrization, am: ArreteMinisteriel, current_page: str
) -> Component:
    header = ['#', 'Paragraphe visé', 'Alineas visés', 'Condition', 'Source', '', '']
    rows = [
        _application_condition_to_row(row, am, rank, current_page)
        for rank, row in enumerate(parametrization.inapplicable_sections)
    ]
    return table_component([header], rows, 'table-sm')


def _get_target_section_id(path: Ints, am: ArreteMinisteriel) -> Optional[str]:
    if not path:
        return None
    section = safe_get_section(path, am)
    if section:
        return section.id
    return None


def _remove_last_word(sentence: str) -> str:
    return ' '.join(sentence.split(' ')[:-1])


def _shorten_text(title: str, max_len: int = 32) -> str:
    if len(title) > max_len:
        return _remove_last_word(title[:max_len]) + ' [...]'
    return title


def _get_section_title_or_error(path: Ints, am: ArreteMinisteriel, titles_sequence: Optional[List[str]]) -> Component:
    titles = get_traversed_titles(path, am)
    section_id = _get_target_section_id(path, am)
    style = {}
    if titles is None:
        style = {'color': 'red'}
        title = f'Introuvable, ce paramètre doit être modifié. (Titres précédents: {titles_sequence})'
    else:
        shortened_titles = [_shorten_text(title) for title in titles]
        joined_titles = ' / '.join(shortened_titles)
        title = html.A(joined_titles, href=f'#{section_id}') if section_id else joined_titles
    return html.Div(html.Span(title, style={**style, 'font-size': '0.8em'}), style={'width': '250px'})


def _wrap_in_paragraphs(strs: List[str]) -> Component:
    return html.Div([html.P(str_) for str_ in strs])


def _small(text: str) -> Component:
    return html.Span(text, style={'font-size': '0.8em'})


def _constrain(component: Component) -> Component:
    style = {
        'display': 'inline-block',
        'max-height': '100px',
        'min-width': '250px',
        'max-width': '250px',
        'font-size': '0.8em',
        'overflow-x': 'auto',
        'overflow-y': 'auto',
    }
    return html.Div(component, style=style)


def _alternative_section_to_row(
    alternative_section: AlternativeSection, am: ArreteMinisteriel, rank: int, current_page: str
) -> List[ExtendedComponent]:
    target_section = alternative_section.targeted_section
    reference_str = _get_section_title_or_error(target_section.path, am, target_section.titles_sequence)
    condition = _small(alternative_section.condition.to_str())
    source_section = alternative_section.source.reference.section
    source = _get_section_title_or_error(source_section.path, am, source_section.titles_sequence)
    new_version = _constrain(_wrap_in_paragraphs(extract_markdown_text(alternative_section.new_text, level=1)))
    href = f'{current_page}/{AMOperation.ADD_ALTERNATIVE_SECTION.value}/{rank}'
    edit = link_button('Éditer', href=href, state=ButtonState.NORMAL_LINK)
    href_copy = f'{current_page}/{AMOperation.ADD_ALTERNATIVE_SECTION.value}/{rank}/copy'
    copy = link_button('Copier', href=href_copy, state=ButtonState.NORMAL_LINK)
    return [str(rank), reference_str, condition, source, new_version, edit, copy]


def _get_alternative_section_table(
    parametrization: Parametrization, am: ArreteMinisteriel, current_page: str
) -> Component:
    header = ['#', 'Paragraphe visé', 'Condition', 'Source', 'Nouvelle version', '', '']
    rows = [
        _alternative_section_to_row(row, am, rank, current_page)
        for rank, row in enumerate(parametrization.alternative_sections)
    ]
    return table_component([header], rows, class_name='table-sm')


def _get_add_condition_button(parent_page: str, status: AMStatus) -> Component:
    state = ButtonState.NORMAL_LINK if status == status.PENDING_PARAMETRIZATION else ButtonState.HIDDEN
    href = f'{parent_page}/{AMOperation.ADD_CONDITION.value}'
    return html.Div(link_button('+ Nouveau', href, state), style={'margin-bottom': '35px'})


def _get_add_alternative_section_button(parent_page: str, status: AMStatus) -> Component:
    state = ButtonState.NORMAL_LINK if status == status.PENDING_PARAMETRIZATION else ButtonState.HIDDEN
    href = f'{parent_page}/{AMOperation.ADD_ALTERNATIVE_SECTION.value}'
    return html.Div(link_button('+ Nouveau', href, state), style={'margin-bottom': '35px'})


def _warning_to_row(warning: AMWarning, am: ArreteMinisteriel, rank: int, current_page: str) -> List[ExtendedComponent]:
    target_section = warning.targeted_section
    reference_str = _get_section_title_or_error(target_section.path, am, target_section.titles_sequence)
    href = f'{current_page}/{AMOperation.ADD_WARNING.value}/{rank}'
    edit = link_button('Éditer', href=href, state=ButtonState.NORMAL_LINK)
    href_copy = f'{current_page}/{AMOperation.ADD_WARNING.value}/{rank}/copy'
    copy = link_button('Copier', href=href_copy, state=ButtonState.NORMAL_LINK)
    return [str(rank), reference_str, warning.text, edit, copy]


def _warnings_table(parametrization: Parametrization, am: ArreteMinisteriel, current_page: str) -> Component:
    header = ['#', 'Paragraphe visé', 'Contenu', '', '']
    rows = [_warning_to_row(row, am, rank, current_page) for rank, row in enumerate(parametrization.warnings)]
    return table_component([header], rows, class_name='table-sm')


def _add_warning_button(parent_page: str, status: AMStatus) -> Component:
    state = ButtonState.NORMAL_LINK if status == status.PENDING_PARAMETRIZATION else ButtonState.HIDDEN
    href = f'{parent_page}/{AMOperation.ADD_WARNING.value}'
    return html.Div(link_button('+ Nouveau', href, state), style={'margin-bottom': '35px'})


def _get_am_component_with_toc(am: ArreteMinisteriel) -> Component:
    return html.Div(
        [
            html.Div([summary_component(am.to_text(), True, False)], className='col-3'),
            html.Div(am_component(am, [], 5), className='col-9'),
        ],
        className='row',
        style={'margin': '0px'},
    )


def _get_parametrization_summary(
    parent_page: str, status: AMStatus, parametrization: Parametrization, am: Optional[ArreteMinisteriel]
) -> Component:
    if status not in (AMStatus.PENDING_PARAMETRIZATION, AMStatus.VALIDATED):
        return html.Div([])
    if not am:
        return error_component('AM introuvable, impossible d\'afficher les paramètres.')
    return html.Div(
        [
            dcc.Link("< Retour à l'arrêté", href=f'/{Endpoint.AM}/{am.id}'),
            html.H4('Sections potentiellement inapplicables'),
            _get_inapplicable_sections_table(parametrization, am, parent_page),
            _get_add_condition_button(parent_page, status),
            html.H4('Paragraphes alternatifs'),
            _get_alternative_section_table(parametrization, am, parent_page),
            _get_add_alternative_section_button(parent_page, status),
            html.H4('Avertissements'),
            _warnings_table(parametrization, am, parent_page),
            _add_warning_button(parent_page, status),
            html.H4('Texte'),
            _get_am_component_with_toc(am),
        ],
        style={
            'position': 'sticky',
            'top': '0px',
            'bottom': '0',
            'height': '75vh',
            'overflow-y': 'auto',
        },
    )


def _structure_am_component(am: ArreteMinisteriel) -> Component:
    style = {
        'position': 'sticky',
        'top': '0px',
        'bottom': '0',
        'height': '70vh',
        'overflow-y': 'auto',
    }
    return html.Div(
        [html.H4('Version actuelle de l\'AM'), html.Div([_get_am_component_with_toc(am)], style=style)], hidden=False
    )


def _structure_tabs(initial_am: ArreteMinisteriel, current_am: Optional[ArreteMinisteriel]) -> Component:
    am_to_display = current_am or initial_am
    return html.Div(_structure_am_component(am_to_display), className='row')


def _get_structure_validation_diff(am_id: str, status: AMStatus) -> Component:
    if status != status.PENDING_STRUCTURE_VALIDATION:
        return html.Div()
    initial_am = DATA_FETCHER.load_initial_am(am_id)
    if not initial_am:
        return html.Div('AM introuvable.')
    return _structure_tabs(initial_am, DATA_FETCHER.load_structured_am(am_id))


def _get_initial_am_component(
    am_id: str, am_status: AMStatus, am: Optional[ArreteMinisteriel], am_page: str
) -> Component:
    if am_status != AMStatus.PENDING_INITIALIZATION:
        return html.Div()
    return am_init_tab(am_id, am, am_page)


def _build_component_based_on_status(
    am_id: str, parent_page: str, am_status: AMStatus, parametrization: Parametrization, am: Optional[ArreteMinisteriel]
) -> Component:
    children = [
        html.Div(
            [
                _get_initial_am_component(am_id, am_status, am, parent_page),
                _get_structure_validation_diff(am_id, am_status),
                _get_parametrization_summary(parent_page, am_status, parametrization, am),
            ],
            style={'margin-bottom': '100px'},
        ),
        _get_buttons(am_status, parent_page),
    ]
    return html.Div(children)


def _make_am_index_component(
    am_id: str, am_status: AMStatus, parent_page: str, parametrization: Parametrization, am: Optional[ArreteMinisteriel]
) -> Component:
    return _build_component_based_on_status(am_id, parent_page, am_status, parametrization, am)


def _add_suffix(rank: int, text: str, status: AMStatus) -> str:
    return text + (' ☑️' if rank < status.step() else '')


def _get_nav(status: AMStatus) -> Component:
    texts = ['1. Initilisation', '2. Structuration', '3. Paramétrage']
    lis = [html.Li(_add_suffix(i, text, status), className='breadcrumb-item') for i, text in enumerate(texts)]
    return html.Ol(
        className='breadcrumb',
        children=lis,
        style={'padding': '7px', 'padding-left': '15px', 'padding-right': '15px', 'font-weight': '300'},
    )


def _get_title_component(
    am_id: str, am_metadata: Optional[AMMetadata], parent_page: str, am_status: AMStatus
) -> Component:
    nav = html.Div(_get_nav(am_status), className='col-6')
    am_id = (am_metadata.nor or am_metadata.cid) if am_metadata else am_id
    cid = am_metadata.cid if am_metadata else am_id
    am_backlink = html.Div(
        dcc.Link(html.H2(f'Arrêté ministériel {am_id}'), href=f'/{Endpoint.AM}/{cid}'), className='col-6'
    )
    row = html.Div(html.Div([am_backlink, nav], className='row'), className='container')
    return html.Div(row, className='am_title')


def _get_body_component(
    am_id: str, parent_page: str, am: Optional[ArreteMinisteriel], am_status: AMStatus, parametrization: Parametrization
) -> Component:
    if not am and am_status != AMStatus.PENDING_INITIALIZATION:
        return html.P('Arrêté introuvable.')
    return _make_am_index_component(am_id, am_status, parent_page, parametrization, am)


def _get_subpage_content(route: str, operation_id: AMOperation) -> Component:
    if operation_id == AMOperation.INIT:
        return am_init_router(route)
    if operation_id in (AMOperation.ADD_ALTERNATIVE_SECTION, AMOperation.ADD_CONDITION, AMOperation.ADD_WARNING):
        return parametrization_router(route)
    if operation_id == AMOperation.EDIT_STRUCTURE:
        return structure_router(route)
    raise NotImplementedError(f'Operation {operation_id} not handled')


def _page(am_id: str, current_page: str) -> Component:
    am_metadata = DATA_FETCHER.load_am_metadata(am_id)
    am_status = DATA_FETCHER.load_am_status(am_id)
    am = DATA_FETCHER.load_most_advanced_am(am_id)  # Fetch initial AM if no parametrization ever done.
    parametrization = DATA_FETCHER.load_or_init_parametrization(am_id)
    body = html.Div(
        _get_body_component(am_id, current_page, am, am_status, parametrization), className='am_page_content'
    )
    return html.Div(
        [
            _get_title_component(am_id, am_metadata, current_page, am_status),
            body,
            html.P(am_id, hidden=True, id=f'{_PREFIX}-am-id'),
            html.P(current_page, hidden=True, id=f'{_PREFIX}-current-page'),
        ]
    )


def _page_with_spinner(am_id: str, current_page: str) -> Component:
    return dbc.Spinner(html.Div(_page(am_id, current_page), id=_LOADER))


def _add_titles_sequences(am_id: str) -> None:
    try:
        parametrization = DATA_FETCHER.load_parametrization(am_id)
        am = DATA_FETCHER.load_most_advanced_am(am_id)
        if am and parametrization:
            new_parametrization = add_titles_sequences(parametrization, am)
            DATA_FETCHER.upsert_new_parametrization(am_id, new_parametrization)
    except Exception:
        warnings.warn(f'Error during titles sequence addition:\n{traceback.format_exc()}')


def _handle_validate_parametrization(am_id: str) -> None:
    _add_titles_sequences(am_id)


def _handle_validate_structure(am_id: str) -> None:
    parametrization = DATA_FETCHER.load_parametrization(am_id)
    if not parametrization:
        return  # parametrization has no risk to be deprecated in this case
    am = DATA_FETCHER.load_most_advanced_am(am_id)
    if not am:
        warnings.warn('Should not happen, structure can be validated only for existing texts.')
        return
    try:
        new_parametrization = regenerate_paths(parametrization, am)
    except UndefinedTitlesSequencesError:
        return
    DATA_FETCHER.upsert_new_parametrization(am_id, new_parametrization)


def _upsert_status(am_id: str, new_status: AMStatus) -> None:
    DATA_FETCHER.upsert_am_status(am_id, new_status)
    if ENVIRONMENT_TYPE == EnvironmentType.PROD:
        send_slack_notification(
            f'AM {am_id} a désormais le statut {new_status.value}', SlackChannel.ENRICHMENT_NOTIFICATIONS
        )


def _upsert_am_status(clicked_button: str, am_id: str) -> None:
    new_status = None
    if clicked_button == _VALIDATE_INITIALIZATION:
        new_status = AMStatus.PENDING_STRUCTURE_VALIDATION
    elif clicked_button == _modal_confirm_button_id('structure'):
        new_status = AMStatus.PENDING_INITIALIZATION
    elif clicked_button == _VALIDATE_STRUCTURE:
        new_status = AMStatus.PENDING_PARAMETRIZATION
    elif clicked_button == _modal_confirm_button_id('parametrization'):
        new_status = AMStatus.PENDING_STRUCTURE_VALIDATION
    elif clicked_button == _VALIDATE_PARAMETRIZATION:
        new_status = AMStatus.VALIDATED
    elif clicked_button == _modal_confirm_button_id('validated'):
        new_status = AMStatus.PENDING_PARAMETRIZATION
    elif clicked_button == _modal_confirm_button_id('reset-structure'):
        new_status = None  # status does not change in this case.
    else:
        raise NotImplementedError(f'Unknown button id {clicked_button}')
    if new_status:
        _upsert_status(am_id, new_status)


def _handle_clicked_button(clicked_button: str, am_id: str) -> None:
    _upsert_am_status(clicked_button, am_id)

    if clicked_button in (_VALIDATE_INITIALIZATION, _modal_confirm_button_id('reset-structure')):
        initial_am = DATA_FETCHER.load_initial_am(am_id)
        if initial_am:
            # structured_am must always exist and be equal to initial_am by default.
            DATA_FETCHER.upsert_structured_am(am_id, add_simple_topics(initial_am))
    if clicked_button == _VALIDATE_PARAMETRIZATION:
        _handle_validate_parametrization(am_id)
    if clicked_button == _VALIDATE_STRUCTURE:
        _handle_validate_structure(am_id)
    if clicked_button == _modal_confirm_button_id('parametrization'):
        _add_titles_sequences(am_id)


_BUTTON_IDS = [
    _VALIDATE_INITIALIZATION,
    _modal_confirm_button_id('structure'),
    _VALIDATE_STRUCTURE,
    _modal_confirm_button_id('parametrization'),
    _modal_confirm_button_id('reset-structure'),
    _VALIDATE_PARAMETRIZATION,
]
_INPUTS = [Input(id_, 'n_clicks') for id_ in _BUTTON_IDS] + [
    Input(f'{_PREFIX}-am-id', 'children'),
    Input(f'{_PREFIX}-current-page', 'children'),
]


@app.callback(Output(_LOADER, 'children'), _INPUTS, prevent_initial_call=True)
def _handle_click(*args):
    all_n_clicks = args[: len(_BUTTON_IDS)]
    am_id, current_page = args[len(_BUTTON_IDS) :]
    for id_, n_clicks in zip(_BUTTON_IDS, all_n_clicks):
        if (n_clicks or 0) >= 1:
            try:
                _handle_clicked_button(id_, am_id)
            except Exception:  # pylint: disable = broad-except
                return error_component(traceback.format_exc())
            if id_ == _VALIDATE_PARAMETRIZATION:
                return dcc.Location(id='redirect-to-am', href=f'/{Endpoint.AM}/{am_id}')
            return _page_with_spinner(am_id, current_page)
    raise PreventUpdate


@app.callback(
    Output(_modal_id(), 'is_open'),
    Input(_modal_button_id(), 'n_clicks'),
    Input(_close_modal_button_id(), 'n_clicks'),
    State(_modal_id(), 'is_open'),
    prevent_initial_call=True,
)
def _toggle_modal(n_clicks, n_clicks_close, is_open):
    if n_clicks or n_clicks_close:
        return not is_open
    return False


parametric_am_list_callbacks(app, _PREFIX)


def router(parent_page: str, route: str) -> Component:
    am_id, operation_id, _ = _extract_am_id_and_operation(route)
    am_metadata = DATA_FETCHER.load_am_metadata(am_id)
    if not am_metadata:
        return html.P(f'404 - Arrêté {am_id} inconnu')
    current_page = parent_page + '/' + am_id
    if operation_id:
        am_status = DATA_FETCHER.load_am_status(am_id)
        subpage_component = _get_subpage_content(route, operation_id)
        return html.Div([_get_title_component(am_id, am_metadata, current_page, am_status), subpage_component])
    return _page_with_spinner(am_id, current_page)
