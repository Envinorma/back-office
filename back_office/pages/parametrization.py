from typing import Dict, List, Optional, Tuple, TypeVar

import dash_bootstrap_components as dbc
from dash import Dash, dcc, html
from dash.development.base_component import Component
from envinorma.models import AMApplicability, ArreteMinisteriel, StructuredText
from envinorma.models.condition import Condition
from envinorma.parametrization import ParameterElement, Parametrization

from back_office.components import error_component
from back_office.components.am_side_nav import page_with_sidebar
from back_office.components.parametrization_components import condition_str, parameter_component
from back_office.routing import Endpoint, Page
from back_office.utils import DATA_FETCHER, generate_id

_PREFIX = 'edit-parametrization'
_AM_ID = generate_id(_PREFIX, 'am-id')


def _new_parameter_element_buttons(am_id: str) -> Component:
    hrefs = [
        ('Nouvelle inapplicabilité', f'/{Endpoint.ADD_INAPPLICABILITY}/{am_id}'),
        ('Nouvelle section alternative', f'/{Endpoint.ADD_ALTERNATIVE_SECTION}/{am_id}'),
        ('Nouvel avertissement', f'/{Endpoint.ADD_WARNING}/{am_id}'),
    ]
    return html.Div([dcc.Link(button_text, className='btn btn-link mr-2', href=href) for button_text, href in hrefs])


T = TypeVar('T')
U = TypeVar('U')


def _group(pairs: List[Tuple[T, U]]) -> Dict[T, List[U]]:
    return {key: [value for key_, value in pairs if key_ == key] for key, _ in pairs}


def _condition_component(
    condition: Condition, section_ids: List[str], section_id_to_section: Dict[str, StructuredText]
) -> Component:
    hrefs = [(section_id_to_section[id_].title.text, f'#{id_}') for id_ in section_ids if id_ in section_id_to_section]
    lis: List[Component] = [html.Li(html.A(title, href=href)) for title, href in hrefs]
    lost = [id_ for id_ in section_ids if id_ not in section_id_to_section]
    if lost:
        lis.append(html.Li(f'{len(lost)} paramètre(s) perdu(s)'))
    return html.Div([html.H6(condition_str(condition)), html.Ul(lis)])


def _parameters_recap(parametrization: Parametrization, sections: List[StructuredText]) -> Component:
    section_id_to_section = {s.id: s for s in sections}
    elements = [*parametrization.alternative_sections, *parametrization.inapplicable_sections]
    condition_to_section_id = _group([(el.condition, el.section_id) for el in elements])
    conditions = [
        _condition_component(condition, section_ids, section_id_to_section)
        for condition, section_ids in sorted(condition_to_section_id.items(), key=lambda x: len(x[1]), reverse=True)
    ]
    return html.Div([html.H4('Liste des conditions'), html.Div(conditions)])


def _lost_parameters_elements(
    parametrization: Parametrization, sections: List[StructuredText], orphan_titles: Dict[str, List[str]]
) -> List[Tuple[Optional[List[str]], ParameterElement]]:
    section_ids = {section.id for section in sections}
    return [(orphan_titles.get(p.section_id), p) for p in parametrization.elements() if p.section_id not in section_ids]


def _lost_parameter_component(
    rank: int, am_id: str, lost_parameter: Tuple[Optional[List[str]], ParameterElement]
) -> Component:
    titles, parameter = lost_parameter
    title_str = 'inconnus' if not titles else ' > '.join(titles)
    return html.Div(
        [
            html.H6(f'Paramètre perdu #{rank}'),
            html.P(f'Titres de la section précédemment visée : {title_str}'),
            parameter_component(am_id, parameter, None, 'danger'),
        ]
    )


def _explanation(number: int) -> str:
    if number == 1:
        return (
            'Le paramètre suivant a été dissocié lors de la dernière édition du contenu de l\'arrêté. '
            'Veuillez le supprimer ou le réaffecter.'
        )
    return (
        'Les paramètres suivants ont été dissociés lors de la dernière édition du contenu de l\'arrêté. '
        'Veuillez les supprimer ou les réaffecter.'
    )


def _lost_parameters(parametrization: Parametrization, am: ArreteMinisteriel) -> Component:
    lost_parameters = _lost_parameters_elements(parametrization, am.descendent_sections(), am.orphan_titles or {})
    if not lost_parameters:
        return html.Div()
    parameters = [_lost_parameter_component(rank + 1, am.id or '', p) for rank, p in enumerate(lost_parameters)]
    title = html.H4('Paramètres perdus', className='text-danger')
    explaination = error_component(_explanation(len(lost_parameters)))
    return html.Div([title, explaination, *parameters, html.Hr()])


def _am_applicability(am_id: str, am_applicability: AMApplicability) -> Component:
    warnings = [html.P(warning) for warning in am_applicability.warnings or ['Aucun avertissement']]
    condition_ = am_applicability.condition_of_inapplicability
    condition = html.P(
        [html.Strong('Cas d\'inapplicabilité : '), condition_str(condition_)]
        if condition_
        else 'Aucune condition d\'inapplicabilité.'
    )
    edit = html.Button('Éditer', className='btn btn-primary ml-2')
    return html.Div(
        [
            html.H6('Avertissements'),
            *warnings,
            condition,
            dcc.Link(edit, href=f'/{Endpoint.AM_APPLICABILITY}/{am_id}'),
        ]
    )


def _section_parameters_summary(am_id: str, section: StructuredText, param: Parametrization) -> Component:
    border = {'border-left': '3px solid #007bffdd', 'padding-left': '10px'}
    parameters = [
        *(param.id_to_inapplicabilities.get(section.id) or []),
        *(param.id_to_alternative_sections.get(section.id) or []),
        *(param.id_to_warnings.get(section.id) or []),
    ]
    return html.Div(
        [
            html.P(section.title.text, className='section-title', id=section.id),
            html.Div([parameter_component(am_id, p, section) for p in parameters])
            if parameters
            else html.P('Aucun paramètre.'),
            *[_section_parameters_summary(am_id, section, param) for section in section.sections],
        ],
        style=border,
    )


def _am_applicability_row(am: ArreteMinisteriel) -> Component:
    return html.Div(
        [
            html.H4('Paramètres concernants l\'arrêté en entier'),
            _am_applicability(am.id or '', am.applicability or AMApplicability()),
            html.Hr(),
        ]
    )


def _buttons(am_id: str) -> Component:
    return html.Div([_new_parameter_element_buttons(am_id), html.Hr()])


def _parametrization(parametrization: Parametrization, am: ArreteMinisteriel) -> Component:
    am_id = am.id or ''
    first_col = dbc.Col(
        [
            _lost_parameters(parametrization, am),
            _am_applicability_row(am),
            _parameters_recap(parametrization, am.descendent_sections()),
        ],
        width=4,
    )
    second_col = dbc.Col(
        [
            html.H4('Paramètres'),
            *[_section_parameters_summary(am_id, section, parametrization) for section in am.sections],
        ]
    )
    return dbc.Row([first_col, second_col])


def _layout(am_id: str) -> Component:
    am = DATA_FETCHER.load_am(am_id)
    if not am:
        return html.H3('AM non initialisé.')
    parametrization = DATA_FETCHER.load_or_init_parametrization(am_id)
    body = _parametrization(parametrization, am)
    return html.Div([_buttons(am_id), body, dcc.Store(data=am_id, id=_AM_ID)])


def _page(am_id: str) -> Component:
    return page_with_sidebar(_layout(am_id), am_id)


def _callbacks(app: Dash) -> None:
    ...


PAGE = Page(_page, _callbacks, False)
