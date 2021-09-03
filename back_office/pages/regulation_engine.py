import json
import os
import random
from typing import Any, Dict, List, Tuple

import dash_bootstrap_components as dbc
import dash_html_components as html
from dash import Dash
from dash.development.base_component import Component
from envinorma.models import ArreteMinisteriel, DetailedClassement, Parameter, ParameterEnum, Regime
from envinorma.parametrization.apply_parameter_values import AMWithApplicability, build_am_with_applicability

from back_office.components import replace_line_breaks
from back_office.components.table import ExtendedComponent, table_component
from back_office.routing import Page
from back_office.utils import DATA_FETCHER, ensure_not_none

_FOLDER = '/Users/remidelbouys/EnviNorma/envinorma-web/db/seeds/ams'
_CLASSEMENTS_FILENAME = '/Users/remidelbouys/EnviNorma/envinorma-web/db/seeds/classements_idf.csv'


def _fetch_all_ams() -> List[ArreteMinisteriel]:
    paths = [os.path.join(_FOLDER, file_) for file_ in os.listdir(_FOLDER)]
    print(f'{len(paths)} AM found.')
    return [ArreteMinisteriel.from_dict(json.load(open(path))) for path in paths]


def _prepare_parameters(classements: List[DetailedClassement]) -> Dict[Parameter, Any]:
    if len(classements) != 1:
        return {}
    classement = classements[0]
    if classement.regime.to_regime() == Regime.A:
        date_key = ParameterEnum.DATE_AUTORISATION
    elif classement.regime.to_regime() == Regime.E:
        date_key = ParameterEnum.DATE_ENREGISTREMENT
    elif classement.regime.to_regime() == Regime.D:
        date_key = ParameterEnum.DATE_DECLARATION
    else:
        raise ValueError(f'Unsupported regime: {classement.regime.to_regime()}')
    return {
        ParameterEnum.RUBRIQUE.value: classement.rubrique,
        ParameterEnum.REGIME.value: classement.regime,
        ParameterEnum.ALINEA.value: classement.alinea,
        ParameterEnum.DATE_INSTALLATION.value: classement.date_mise_en_service,
        date_key.value: classement.date_autorisation,
    }


def _apply_parameters(classements: List[DetailedClassement], am: ArreteMinisteriel) -> AMWithApplicability:
    parameters = _prepare_parameters(classements)
    parametrization = DATA_FETCHER.load_or_init_parametrization(am.id or '')
    return build_am_with_applicability(am, parametrization, parameters)


def _compute_applicable_versions(
    am_id_to_classements: Dict[str, List[DetailedClassement]], ams: Dict[str, ArreteMinisteriel]
) -> List[Tuple[AMWithApplicability, List[DetailedClassement]]]:
    applicable_ams: List[Tuple[AMWithApplicability, List[DetailedClassement]]] = []
    for am_id, classements in am_id_to_classements.items():
        applicable_ams.append((_apply_parameters(classements, ams[am_id]), classements))
    return applicable_ams


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
    classements: List[DetailedClassement], ams: Dict[str, ArreteMinisteriel]
) -> Dict[str, List[DetailedClassement]]:
    applicable_pairs = [
        (classement, am_id) for classement in classements for am_id, am in ams.items() if _match(am, classement)
    ]
    result: Dict[str, List[DetailedClassement]] = {}
    for classement, am_id in applicable_pairs:
        if am_id not in result:
            result[am_id] = []
        result[am_id].append(classement)
    return result


def _compute_arrete_list(
    classements: List[DetailedClassement],
) -> List[Tuple[AMWithApplicability, List[DetailedClassement]]]:
    all_ams = _fetch_all_ams()
    ams: Dict[str, ArreteMinisteriel] = {ensure_not_none(am.id): am for am in all_ams}
    return _compute_applicable_versions(_get_am_id_to_classements(classements, ams), ams)


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
    import pandas  # type: ignore # Hacky: to avoid adding new dependency

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


def _arrete_li(rank: int, arrete: AMWithApplicability, classements: List[DetailedClassement]) -> Component:
    classement_hints = {f'{cl.rubrique} {cl.regime.value}' for cl in classements}
    to_append = html.Span(' - '.join(classement_hints), style={'color': 'grey'})
    return html.Li(
        [
            dbc.Checkbox(checked=arrete.applicable),
            html.Span(' '),
            arrete.arrete.short_title + ' - ',
            to_append,
            _tooltip(rank, arrete.warnings),
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


def _am_sort_score(am_: AMWithApplicability) -> Tuple:
    return -am_.applicable, -_regime_score(am_.arrete.classements[0].regime), am_.arrete.short_title


def _ams_list(arretes: List[Tuple[AMWithApplicability, List[DetailedClassement]]]) -> Component:
    sorted_arretes = sorted(arretes, key=lambda x: _am_sort_score(x[0]))
    return html.Ul(
        [_arrete_li(rank, arrete, classements) for rank, (arrete, classements) in enumerate(sorted_arretes)],
        className='list-unstyled',
    )


def _arretes_component(arretes: List[Tuple[AMWithApplicability, List[DetailedClassement]]]) -> Component:
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
