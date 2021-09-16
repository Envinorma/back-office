from typing import Dict, List, Optional

from dash import Dash, dcc, html
from dash.development.base_component import Component
from envinorma.io.markdown import extract_markdown_text
from envinorma.models import AMMetadata, ArreteMinisteriel
from envinorma.models.structured_text import StructuredText
from envinorma.parametrization import AlternativeSection, AMWarning, InapplicableSection, Parametrization

from back_office.components import ButtonState, error_component, link_button
from back_office.components.table import ExtendedComponent, table_component
from back_office.routing import Endpoint, Page
from back_office.utils import DATA_FETCHER, generate_id

_PREFIX = 'edit-parametrization'
_AM_ID = generate_id(_PREFIX, 'am-id')


def _human_alinea_tuple(ints: Optional[List[int]]) -> str:
    if not ints:
        return 'Tous'
    return ', '.join(map(str, sorted(ints)))


def _application_condition_to_row(
    inapplicable_section: InapplicableSection, am: ArreteMinisteriel, id_to_section: Dict[str, StructuredText]
) -> List[ExtendedComponent]:
    reference_str = _get_section_title_or_error(inapplicable_section.section_id, am, id_to_section)
    alineas = _human_alinea_tuple(inapplicable_section.alineas)
    condition = _small(inapplicable_section.condition.to_str())
    href = f'/{Endpoint.ADD_INAPPLICABILITY}/{am.id}/{inapplicable_section.id}'
    edit = link_button('Éditer', href=href, state=ButtonState.NORMAL_LINK)
    copy = link_button('Copier', href=f'/{href}/copy', state=ButtonState.NORMAL_LINK)
    return [reference_str, alineas, condition, edit, copy]


def _inapplicable_sections_table(
    parametrization: Parametrization, am: ArreteMinisteriel, id_to_section: Dict[str, StructuredText]
) -> Component:
    header = ['Paragraphe visé', 'Alineas visés', 'Condition', '', '']
    rows = [_application_condition_to_row(row, am, id_to_section) for row in parametrization.inapplicable_sections]
    return table_component([header], rows, 'table-sm')  # type: ignore


def _remove_last_word(sentence: str) -> str:
    return ' '.join(sentence.split(' ')[:-1])


def _shorten_text(title: str, max_len: int = 80) -> str:
    if len(title) > max_len:
        return _remove_last_word(title[:max_len]) + ' [...]'
    return title


def _get_section_title_or_error(
    section_id: str, am: ArreteMinisteriel, id_to_section: Dict[str, StructuredText]
) -> Component:
    section = id_to_section.get(section_id)
    style = {}
    if section is None:
        style = {'color': 'red'}
        old_titles = (am.orphan_titles or {}).get(section_id) or []
        title = f'Introuvable, ce paramètre doit être modifié. (Titres précédents: {old_titles})'
    else:
        href = f'/{Endpoint.AM}/{am.id or ""}/1#{section_id}'
        title = html.A(_shorten_text(section.title.text), href=href, target='_blank')
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
    alternative_section: AlternativeSection, am: ArreteMinisteriel, id_to_section: Dict[str, StructuredText]
) -> List[ExtendedComponent]:
    reference_str = _get_section_title_or_error(alternative_section.section_id, am, id_to_section)
    condition = _small(alternative_section.condition.to_str())
    new_version = _constrain(_wrap_in_paragraphs(extract_markdown_text(alternative_section.new_text, level=1)))
    href = f'/{Endpoint.ADD_ALTERNATIVE_SECTION}/{am.id}/{alternative_section.id}'
    edit = link_button('Éditer', href=href, state=ButtonState.NORMAL_LINK)
    copy = link_button('Copier', href=f'{href}/copy', state=ButtonState.NORMAL_LINK)
    return [reference_str, condition, new_version, edit, copy]


def _alternative_section_table(
    parametrization: Parametrization, am: ArreteMinisteriel, id_to_section: Dict[str, StructuredText]
) -> Component:
    header = ['Paragraphe visé', 'Condition', 'Nouvelle version', '', '']
    rows = [_alternative_section_to_row(row, am, id_to_section) for row in parametrization.alternative_sections]
    return table_component([header], rows, class_name='table-sm')  # type: ignore


def _button_add(href: str) -> Component:
    return dcc.Link(html.Button('+ Ajouter', className='btn btn-link mb-3'), href=href)


def _add_condition_button(am_id: str) -> Component:
    href = f'/{Endpoint.ADD_INAPPLICABILITY}/{am_id}'
    return _button_add(href)


def _add_alternative_section_button(am_id: str) -> Component:
    href = f'/{Endpoint.ADD_ALTERNATIVE_SECTION}/{am_id}'
    return _button_add(href)


def _warning_to_row(
    warning: AMWarning, am: ArreteMinisteriel, id_to_section: Dict[str, StructuredText]
) -> List[ExtendedComponent]:
    reference_str = _get_section_title_or_error(warning.section_id, am, id_to_section)
    href = f'/{Endpoint.ADD_WARNING}/{am.id}/{warning.id}'
    edit = link_button('Éditer', href=href, state=ButtonState.NORMAL_LINK)
    copy = link_button('Copier', href=f'/{href}/copy', state=ButtonState.NORMAL_LINK)
    return [reference_str, warning.text, edit, copy]


def _warnings_table(
    parametrization: Parametrization, am: ArreteMinisteriel, id_to_section: Dict[str, StructuredText]
) -> Component:
    header = ['Paragraphe visé', 'Contenu', '', '']
    rows = [_warning_to_row(row, am, id_to_section) for row in parametrization.warnings]
    return table_component([header], rows, class_name='table-sm')  # type: ignore


def _add_warning_button(am_id: str) -> Component:
    href = f'/{Endpoint.ADD_WARNING}/{am_id}'
    return _button_add(href)


def _get_parametrization_summary(parametrization: Parametrization, am: Optional[ArreteMinisteriel]) -> Component:
    if not am:
        return error_component('AM introuvable, impossible d\'afficher les paramètres.')
    id_to_section = {section.id: section for section in am.descendent_sections()}
    am_id = am.id or ''
    return html.Div(
        [
            dcc.Link("< Retour à l'arrêté", href=f'/{Endpoint.AM}/{am_id}'),
            html.H4('Sections potentiellement inapplicables'),
            _inapplicable_sections_table(parametrization, am, id_to_section),
            _add_condition_button(am_id),
            html.H4('Paragraphes alternatifs'),
            _alternative_section_table(parametrization, am, id_to_section),
            _add_alternative_section_button(am_id),
            html.H4('Avertissements'),
            _warnings_table(parametrization, am, id_to_section),
            _add_warning_button(am_id),
        ]
    )


def _make_am_index_component(parametrization: Parametrization, am: Optional[ArreteMinisteriel]) -> Component:
    return html.Div(_get_parametrization_summary(parametrization, am), style={'margin-bottom': '100px'})


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


def _add_callbacks(app: Dash) -> None:
    pass


def _layout(am_id: str) -> Component:
    am_metadata = DATA_FETCHER.load_am_metadata(am_id)
    if not am_metadata:
        return html.P(f'404 - Arrêté {am_id} inconnu')
    return _page(am_id)


PAGE: Page = Page(_layout, _add_callbacks, True)
