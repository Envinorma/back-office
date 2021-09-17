from typing import Dict, List, Optional, Tuple

import dash_bootstrap_components as dbc
from dash import Dash, dcc, html
from dash.development.base_component import Component
from envinorma.models import AMApplicability, AMMetadata, ArreteMinisteriel, StructuredText
from envinorma.parametrization import ParameterElement, Parametrization

from back_office.routing import Endpoint, Page
from back_office.utils import DATA_FETCHER, generate_id

from .components import condition_str, parameter_component

_PREFIX = 'edit-parametrization'
_AM_ID = generate_id(_PREFIX, 'am-id')


def _new_parameter_element_buttons(am_id: str) -> Component:
    hrefs = [
        ('Nouvelle inapplicabilité', f'/{Endpoint.ADD_INAPPLICABILITY}/{am_id}'),
        ('Nouvelle section alternative', f'/{Endpoint.ADD_ALTERNATIVE_SECTION}/{am_id}'),
        ('Nouvel avertissement', f'/{Endpoint.ADD_WARNING}/{am_id}'),
    ]
    return html.Div(
        [
            dcc.Link(html.Button(button_text, className='btn btn-primary ml-2'), href=href)
            for button_text, href in hrefs
        ],
        className='mb-3',
    )


def _lost_parameters_elements(
    parametrization: Parametrization, sections: List[StructuredText], orphan_titles: Dict[str, List[str]]
) -> List[Tuple[Optional[List[str]], ParameterElement]]:
    section_ids = {section.id for section in sections}
    return [(orphan_titles.get(p.section_id), p) for p in parametrization.elements() if p.section_id not in section_ids]


def _lost_parameter_component(am_id: str, lost_parameter: Tuple[Optional[List[str]], ParameterElement]) -> Component:
    titles, parameter = lost_parameter
    title_str = 'inconnus' if not titles else ' > '.join(titles)
    return html.Div(
        [html.P(f'Titres de la section précédemment visée : {title_str}'), parameter_component(am_id, parameter, None)]
    )


def _lost_parameters(parametrization: Parametrization, am: ArreteMinisteriel) -> Component:
    _lost_parameters = _lost_parameters_elements(parametrization, am.descendent_sections(), am.orphan_titles or {})
    if not _lost_parameters:
        return html.Div()
    parameters = [_lost_parameter_component(am.id or '', p) for p in _lost_parameters]
    return html.Div([html.H5('Paramètres perdus'), *parameters])


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
            html.P(section.title.text, className='section-title'),
            html.Div([parameter_component(am_id, p, section) for p in parameters])
            if parameters
            else html.P('Aucun paramètre.'),
            *[_section_parameters_summary(am_id, section, param) for section in section.sections],
        ],
        style=border,
    )


def _am_applicability_row(am: ArreteMinisteriel) -> Component:
    return dbc.Card(
        [
            dbc.CardHeader('Paramètres concernants l\'arrêté en entier'),
            dbc.CardBody(_am_applicability(am.id or '', am.applicability or AMApplicability())),
        ]
    )


def _parametrization(parametrization: Parametrization, am: ArreteMinisteriel) -> Component:
    return html.Div(
        [
            _new_parameter_element_buttons(am.id or ''),
            _lost_parameters(parametrization, am),
            _am_applicability_row(am),
            html.H4('Paramètres', className='mt-5'),
            *[_section_parameters_summary(am.id or '', section, parametrization) for section in am.sections],
        ]
    )


def _title_component(am_id: str, am_metadata: Optional[AMMetadata]) -> Component:
    am_id = (am_metadata.nor or am_metadata.cid) if am_metadata else am_id
    cid = am_metadata.cid if am_metadata else am_id
    return html.H3(f'AM {cid}')


def _page(am_id: str) -> Component:
    am_metadata = DATA_FETCHER.load_am_metadata(am_id)
    am = DATA_FETCHER.load_most_advanced_am(am_id)  # Fetch initial AM if no parametrization ever done.
    if not am:
        return html.H3('AM non initialisé.')
    parametrization = DATA_FETCHER.load_or_init_parametrization(am_id)
    body = _parametrization(parametrization, am)
    return html.Div([_title_component(am_id, am_metadata), body, dcc.Store(data=am_id, id=_AM_ID)])


def _add_callbacks(app: Dash) -> None:
    pass


def _layout(am_id: str) -> Component:
    am_metadata = DATA_FETCHER.load_am_metadata(am_id)
    if not am_metadata:
        return html.P(f'404 - Arrêté {am_id} inconnu')
    return _page(am_id)


PAGE: Page = Page(_layout, _add_callbacks, True)
