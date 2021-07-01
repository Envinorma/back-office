import json
import math
import os
import random
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

import dash_bootstrap_components as dbc
import dash_html_components as html
from dash import Dash
from dash.development.base_component import Component
from envinorma.models import ArreteMinisteriel, DateParameterDescriptor, DetailedClassement, Regime, VersionDescriptor

from back_office.components import replace_line_breaks
from back_office.components.table import ExtendedComponent, table_component
from back_office.routing import Page
from back_office.utils import ensure_not_none

_FOLDER = '/Users/remidelbouys/EnviNorma/envinorma-web/db/seeds/enriched_arretes'
_CLASSEMENTS_FILENAME = '/Users/remidelbouys/EnviNorma/envinorma-web/db/seeds/classements_idf.csv'


def _fetch_all_ams() -> List[ArreteMinisteriel]:
    paths = [os.path.join(_FOLDER, file_) for file_ in os.listdir(_FOLDER)]
    print(f'{len(paths)} AM found.')
    return [ArreteMinisteriel.from_dict(json.load(open(path))) for path in paths]


def _is_default(am: ArreteMinisteriel) -> bool:
    version_descriptor: VersionDescriptor = ensure_not_none(am.version_descriptor)
    unknown_date_1 = not version_descriptor.aed_date.unknown_classement_date_version
    unknown_date_2 = not version_descriptor.date_de_mise_en_service.unknown_classement_date_version
    return unknown_date_1 and unknown_date_2


def _date_match(parameter: DateParameterDescriptor, date_: Optional[date]) -> bool:
    if not parameter.is_used_in_parametrization:
        return True
    if date_ and parameter.unknown_classement_date_version:
        return False
    if not date_:
        if not parameter.unknown_classement_date_version:
            return False
        return True
    left_value = parameter.left_value.toordinal() if parameter.left_value else -math.inf
    right_value = parameter.right_value.toordinal() if parameter.right_value else math.inf
    return left_value <= date_.toordinal() < right_value


def _dates_match(am: ArreteMinisteriel, aed_date: Optional[date], installation_date: Optional[date]) -> bool:
    version: VersionDescriptor = ensure_not_none(am.version_descriptor)
    return _date_match(version.aed_date, aed_date) and _date_match(version.date_de_mise_en_service, installation_date)


def _choose_correct_version(classement: DetailedClassement, am_versions: List[ArreteMinisteriel]) -> ArreteMinisteriel:
    if len(am_versions) == 1:
        version: VersionDescriptor = ensure_not_none(am_versions[0].version_descriptor)
        assert not version.aed_date.is_used_in_parametrization
        assert not version.date_de_mise_en_service.is_used_in_parametrization
    aed_date = classement.date_autorisation
    installation_date = classement.date_mise_en_service
    matches = [am for am in am_versions if _dates_match(am, aed_date, installation_date)]
    if len(matches) != 1:
        raise ValueError(f'There must be exactly one match, got {len(matches)}')
    return matches[0]


def _deduce_applicable_versions(
    am_id_to_classements: Dict[str, List[DetailedClassement]],
    default_ams: Dict[str, ArreteMinisteriel],
    am_versions: Dict[str, List[ArreteMinisteriel]],
) -> List[Tuple[ArreteMinisteriel, List[DetailedClassement]]]:
    applicable_ams: List[Tuple[ArreteMinisteriel, List[DetailedClassement]]] = []
    for am_id, classements in am_id_to_classements.items():
        if len(classements) == 1:
            am_version = _choose_correct_version(classements[0], am_versions[am_id])
        else:
            am_version = default_ams[am_id]
        applicable_ams.append((am_version, classements))
    return applicable_ams


def _group_by_id(ams: List[ArreteMinisteriel]) -> Dict[str, List[ArreteMinisteriel]]:
    result: Dict[str, List[ArreteMinisteriel]] = {}
    for am in ams:
        am_id: str = ensure_not_none(am.id)
        if am_id not in result:
            result[am_id] = []
        result[am_id].append(am)
    return result


def _am_simple_regime(regime: Regime) -> str:
    if regime == Regime.DC:
        return 'D'
    return regime.value


def _match(am: ArreteMinisteriel, classement: DetailedClassement) -> bool:
    for am_classement in am.classements:
        classement_match = classement.regime.to_simple_regime() == _am_simple_regime(am_classement.regime)
        rubrique_match = classement.rubrique == am_classement.rubrique
        if classement_match and rubrique_match:
            return True
    return False


def _get_am_id_to_classements(
    classements: List[DetailedClassement], default_ams: Dict[str, ArreteMinisteriel]
) -> Dict[str, List[DetailedClassement]]:
    applicable_pairs = [
        (classement, am_id) for classement in classements for am_id, am in default_ams.items() if _match(am, classement)
    ]
    result: Dict[str, List[DetailedClassement]] = {}
    for classement, am_id in applicable_pairs:
        if am_id not in result:
            result[am_id] = []
        result[am_id].append(classement)
    return result


def _compute_arrete_list(
    classements: List[DetailedClassement],
) -> List[Tuple[ArreteMinisteriel, List[DetailedClassement]]]:
    all_ams = _fetch_all_ams()
    default_ams: Dict[str, ArreteMinisteriel] = {ensure_not_none(am.id): am for am in all_ams if _is_default(am)}
    am_versions = _group_by_id(all_ams)
    return _deduce_applicable_versions(_get_am_id_to_classements(classements, default_ams), default_ams, am_versions)


def _row_to_classement(record: Dict[str, Any]) -> DetailedClassement:

    key_dates = ['date_autorisation', 'date_mise_en_service', 'last_substantial_modif_date']
    for key in key_dates:
        record[key] = record[key] or None
    classement = DetailedClassement(**record)
    simple_regimes = (
        classement.regime.A,
        classement.regime.E,
        classement.regime.D,
        classement.regime.NC,
        classement.regime.UNKNOWN,
    )
    assert classement.regime in (simple_regimes)
    assert classement.regime_acte in (simple_regimes)
    return classement


def _classements() -> List[DetailedClassement]:
    import pandas  # Hacky: to avoid adding new dependency

    dataframe = pandas.read_csv(
        _CLASSEMENTS_FILENAME,
        dtype='str',
        index_col='Unnamed: 0',
        na_values=None,
        parse_dates=['date_autorisation'],
        nrows=100,
    ).fillna('')
    return [_row_to_classement(record) for record in dataframe.to_dict(orient='records')]


def _classement_row(classement: DetailedClassement) -> List[ExtendedComponent]:
    return [
        classement.rubrique,
        classement.regime.value,
        classement.alinea or '',
        str(classement.date_mise_en_service),
        str(classement.date_autorisation),
    ]


def _classement_importance(classement: DetailedClassement) -> Tuple:
    return -_regime_score(classement.regime.to_regime() or Regime.NC), classement.rubrique


def _classements_component(classements: List[DetailedClassement]) -> Component:
    rows = [_classement_row(classement) for classement in sorted(classements, key=_classement_importance)]
    table = table_component([['Rubrique', 'Régime', 'Alinea', 'Date de mise en service', 'Date d\'autorisation']], rows)
    return html.Div([html.H4('Classements'), table])


def _tooltip(rank: int, warnings: List[str]) -> Component:
    id_ = f'applicability-warning-{rank}'
    if not warnings:
        return html.Span()
    content = replace_line_breaks('\n'.join(warnings))
    return html.Span(
        [
            html.Span(' '),
            dbc.Tooltip(content, target=id_),
            html.Span('⚠️', id=id_, style={'cursor': 'pointer'}),
        ]
    )


def _arrete_li(rank: int, arrete: ArreteMinisteriel, classements: List[DetailedClassement]) -> Component:
    classement_hints = {f'{cl.rubrique} {cl.regime.value}' for cl in classements}
    to_append = html.Span(' - '.join(classement_hints), style={'color': 'grey'})
    version: VersionDescriptor = ensure_not_none(arrete.version_descriptor)
    return html.Li(
        [
            dbc.Checkbox(checked=version.applicable),
            html.Span(' '),
            arrete.short_title + ' - ',
            to_append,
            _tooltip(rank, version.applicability_warnings),
        ]
    )


def _ap() -> Component:
    return html.Div(
        [
            html.H4('Arrêtés préfectoraux associés'),
            html.Ul(
                html.Li('Arrêté proposant Prescriptions Spéciales-IC-20-003 - 21/01/20'), className='list-unstyled'
            ),
        ],
        className='col mt-4',
    )


def _regime_score(regime: Regime) -> int:
    if regime == Regime.A:
        return 3
    if regime == Regime.E:
        return 2
    if regime in (Regime.D, Regime.DC):
        return 1
    return 0


def _am_sort_score(am: ArreteMinisteriel) -> Tuple:
    version: VersionDescriptor = ensure_not_none(am.version_descriptor)
    return -version.applicable, -_regime_score(am.classements[0].regime), am.short_title


def _ams_list(arretes: List[Tuple[ArreteMinisteriel, List[DetailedClassement]]]) -> Component:
    sorted_arretes = sorted(arretes, key=lambda x: _am_sort_score(x[0]))
    return html.Ul(
        [_arrete_li(rank, arrete, classements) for rank, (arrete, classements) in enumerate(sorted_arretes)],
        className='list-unstyled',
    )


def _arretes_component(arretes: List[Tuple[ArreteMinisteriel, List[DetailedClassement]]]) -> Component:
    ams = html.Div([html.H4('Arrêtés ministériels associés'), _ams_list(arretes)], className='col mt-4')
    return html.Div([ams, _ap()], className='row')


def layout() -> Component:
    all_classements = _classements()
    classements = random.sample(all_classements, k=15)
    arretes = _compute_arrete_list(classements)
    return html.Div(
        [html.H3('Moteur de réglementation.'), _classements_component(classements), _arretes_component(arretes)]
    )


def _callbacks(app: Dash) -> None:
    ...


PAGE = Page(layout, _callbacks)
