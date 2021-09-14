import traceback
import warnings
from typing import List, Optional

from dash import Dash, Input, Output, dcc, html
from dash.development.base_component import Component
from envinorma.io.markdown import extract_markdown_text
from envinorma.models import AMMetadata, ArreteMinisteriel, Ints
from envinorma.parametrization import AlternativeSection, AMWarning, InapplicableSection, Parametrization
from envinorma.parametrization.resync import add_titles_sequences

from back_office.components import ButtonState, button, error_component, link_button
from back_office.components.am_component import am_component
from back_office.components.summary_component import summary_component
from back_office.components.table import ExtendedComponent, table_component
from back_office.config import ENVIRONMENT_TYPE, EnvironmentType
from back_office.helpers.slack import SlackChannel, send_slack_notification
from back_office.helpers.texts import get_traversed_titles, safe_get_section
from back_office.routing import Endpoint, Page
from back_office.utils import DATA_FETCHER, generate_id

_PREFIX = 'edit-parametrization'
_AM_ID = generate_id(_PREFIX, 'am-id')
_VALIDATE_PARAMETRIZATION = generate_id(_PREFIX, 'validate-parametrization')
_LOADER = generate_id(_PREFIX, 'loading-output')


def _parametrization_edition_buttons() -> Component:
    return button('Valider le paramétrage', id_=_VALIDATE_PARAMETRIZATION, state=ButtonState.NORMAL)


def _human_alinea_tuple(ints: Optional[List[int]]) -> str:
    if not ints:
        return 'Tous'
    return ', '.join(map(str, sorted(ints)))


def _application_condition_to_row(
    inapplicable_section: InapplicableSection, am: ArreteMinisteriel, rank: int
) -> List[ExtendedComponent]:
    target_section = inapplicable_section.targeted_entity.section
    reference_str = _get_section_title_or_error(target_section.path, am, target_section.titles_sequence)
    alineas = _human_alinea_tuple(inapplicable_section.targeted_entity.outer_alinea_indices)
    condition = _small(inapplicable_section.condition.to_str())
    source_section = inapplicable_section.source.reference.section
    source = _get_section_title_or_error(source_section.path, am, source_section.titles_sequence)
    href = f'/{Endpoint.ADD_CONDITION}/{am.id}/{rank}'
    edit = link_button('Éditer', href=href, state=ButtonState.NORMAL_LINK)
    href_copy = f'/{Endpoint.ADD_CONDITION}/{am.id}/{rank}/copy'
    copy = link_button('Copier', href=href_copy, state=ButtonState.NORMAL_LINK)
    return [str(rank), reference_str, alineas, condition, source, edit, copy]


def _get_inapplicable_sections_table(parametrization: Parametrization, am: ArreteMinisteriel) -> Component:
    header = ['#', 'Paragraphe visé', 'Alineas visés', 'Condition', 'Source', '', '']
    rows = [
        _application_condition_to_row(row, am, rank) for rank, row in enumerate(parametrization.inapplicable_sections)
    ]
    return table_component([header], rows, 'table-sm')  # type: ignore


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
    alternative_section: AlternativeSection, am: ArreteMinisteriel, rank: int
) -> List[ExtendedComponent]:
    target_section = alternative_section.targeted_section
    reference_str = _get_section_title_or_error(target_section.path, am, target_section.titles_sequence)
    condition = _small(alternative_section.condition.to_str())
    source_section = alternative_section.source.reference.section
    source = _get_section_title_or_error(source_section.path, am, source_section.titles_sequence)
    new_version = _constrain(_wrap_in_paragraphs(extract_markdown_text(alternative_section.new_text, level=1)))
    href = f'/{Endpoint.ADD_ALTERNATIVE_SECTION}/{am.id}/{rank}'
    edit = link_button('Éditer', href=href, state=ButtonState.NORMAL_LINK)
    copy = link_button('Copier', href=f'{href}/copy', state=ButtonState.NORMAL_LINK)
    return [str(rank), reference_str, condition, source, new_version, edit, copy]


def _get_alternative_section_table(parametrization: Parametrization, am: ArreteMinisteriel) -> Component:
    header = ['#', 'Paragraphe visé', 'Condition', 'Source', 'Nouvelle version', '', '']
    rows = [_alternative_section_to_row(row, am, rank) for rank, row in enumerate(parametrization.alternative_sections)]
    return table_component([header], rows, class_name='table-sm')  # type: ignore


def _get_add_condition_button(am_id: str) -> Component:
    href = f'/{Endpoint.ADD_CONDITION}/{am_id}'
    return html.Div(link_button('+ Nouveau', href, ButtonState.NORMAL_LINK), style={'margin-bottom': '35px'})


def _get_add_alternative_section_button(am_id: str) -> Component:
    href = f'/{Endpoint.ADD_ALTERNATIVE_SECTION}/{am_id}'
    return html.Div(link_button('+ Nouveau', href, ButtonState.NORMAL_LINK), style={'margin-bottom': '35px'})


def _warning_to_row(warning: AMWarning, am: ArreteMinisteriel, rank: int) -> List[ExtendedComponent]:
    target_section = warning.targeted_section
    reference_str = _get_section_title_or_error(target_section.path, am, target_section.titles_sequence)
    href = f'/{Endpoint.ADD_WARNING}/{am.id}/{rank}'
    edit = link_button('Éditer', href=href, state=ButtonState.NORMAL_LINK)
    href_copy = f'/{Endpoint.ADD_WARNING}/{am.id}/{rank}/copy'
    copy = link_button('Copier', href=href_copy, state=ButtonState.NORMAL_LINK)
    return [str(rank), reference_str, warning.text, edit, copy]


def _warnings_table(parametrization: Parametrization, am: ArreteMinisteriel) -> Component:
    header = ['#', 'Paragraphe visé', 'Contenu', '', '']
    rows = [_warning_to_row(row, am, rank) for rank, row in enumerate(parametrization.warnings)]
    return table_component([header], rows, class_name='table-sm')  # type: ignore


def _add_warning_button(am_id: str) -> Component:
    href = f'/{Endpoint.ADD_WARNING}/{am_id}'
    return html.Div(link_button('+ Nouveau', href, ButtonState.NORMAL_LINK), style={'margin-bottom': '35px'})


def _get_am_component_with_toc(am: ArreteMinisteriel) -> Component:
    return html.Div(
        [
            html.Div([summary_component(am.to_text(), True, False)], className='col-3'),
            html.Div(am_component(am, [], 5), className='col-9'),
        ],
        className='row',
        style={'margin': '0px'},
    )


def _get_parametrization_summary(parametrization: Parametrization, am: Optional[ArreteMinisteriel]) -> Component:
    if not am:
        return error_component('AM introuvable, impossible d\'afficher les paramètres.')
    am_id = am.id or ''
    return html.Div(
        [
            dcc.Link("< Retour à l'arrêté", href=f'/{Endpoint.AM}/{am_id}'),
            html.H4('Sections potentiellement inapplicables'),
            _get_inapplicable_sections_table(parametrization, am),
            _get_add_condition_button(am_id),
            html.H4('Paragraphes alternatifs'),
            _get_alternative_section_table(parametrization, am),
            _get_add_alternative_section_button(am_id),
            html.H4('Avertissements'),
            _warnings_table(parametrization, am),
            _add_warning_button(am_id),
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


def _make_am_index_component(parametrization: Parametrization, am: Optional[ArreteMinisteriel]) -> Component:
    children = [
        html.Div(_get_parametrization_summary(parametrization, am), style={'margin-bottom': '100px'}),
        _parametrization_edition_buttons(),
    ]
    return html.Div(children)


def _get_title_component(am_id: str, am_metadata: Optional[AMMetadata]) -> Component:
    am_id = (am_metadata.nor or am_metadata.cid) if am_metadata else am_id
    cid = am_metadata.cid if am_metadata else am_id
    am_backlink = html.Div(
        dcc.Link(html.H2(f'Arrêté ministériel {am_id}'), href=f'/{Endpoint.AM}/{cid}'), className='col-6'
    )
    row = html.Div(html.Div(am_backlink, className='row'), className='container')
    return html.Div(row, className='am_title')


def _get_body_component(am: Optional[ArreteMinisteriel], parametrization: Parametrization) -> Component:
    return _make_am_index_component(parametrization, am)


def _page(am_id: str) -> Component:
    am_metadata = DATA_FETCHER.load_am_metadata(am_id)
    am = DATA_FETCHER.load_most_advanced_am(am_id)  # Fetch initial AM if no parametrization ever done.
    parametrization = DATA_FETCHER.load_or_init_parametrization(am_id)
    body = html.Div(_get_body_component(am, parametrization), className='am_page_content')
    return html.Div([_get_title_component(am_id, am_metadata), body, dcc.Store(data=am_id, id=_AM_ID)])


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
    _add_titles_sequences(am_id)  # TODO : Enlever et enlever le bouton valider le paramétrage


def _add_callbacks(app: Dash) -> None:
    @app.callback(
        Output(_LOADER, 'children'),
        [Input(_VALIDATE_PARAMETRIZATION, 'n_clicks'), Input(_AM_ID, 'data')],
        prevent_initial_call=True,
    )
    def _handle_click(_, am_id: str):
        _handle_validate_parametrization(am_id)
        return dcc.Location(id='redirect-to-am', href=f'/{Endpoint.AM}/{am_id}')


def _layout(am_id: str) -> Component:
    am_metadata = DATA_FETCHER.load_am_metadata(am_id)
    if not am_metadata:
        return html.P(f'404 - Arrêté {am_id} inconnu')
    return _page(am_id)


PAGE: Page = Page(_layout, _add_callbacks, True)
