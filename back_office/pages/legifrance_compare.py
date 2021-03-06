import traceback
from datetime import date
from typing import Optional, Tuple

import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, State, dcc, html
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
from leginorma import LegifranceRequestError

from back_office.components import error_component
from back_office.components.diff import diff_component
from back_office.helpers.diff import compute_am_diff
from back_office.helpers.legifrance import NoConsolidationError, extract_legifrance_am
from back_office.routing import Endpoint, Page
from back_office.utils import generate_id

_DATE_BEFORE = generate_id(__file__, 'before-date')
_DATE_AFTER = generate_id(__file__, 'after-date')
_AM_ID = generate_id(__file__, 'am-id')
_FORM_OUTPUT = generate_id(__file__, 'form-output')
_SUBMIT = generate_id(__file__, 'submit')
_DIFF = generate_id(__file__, 'diff')


class _FormError(Exception):
    pass


def _date_picker(id_: str, initial_date: Optional[date]) -> Component:
    return dbc.Input(id=id_, type='date', className='form-control', value=initial_date)


def _before_date(date: Optional[date]) -> Component:
    return html.Div(
        [html.Label('Date de la version de référence', htmlFor=_DATE_BEFORE), _date_picker(_DATE_BEFORE, date)],
        className='col-md-12',
    )


def _after_date(date: Optional[date]) -> Component:
    return html.Div(
        [html.Label('Date de la version à comparer', htmlFor=_DATE_AFTER), _date_picker(_DATE_AFTER, date)],
        className='col-md-12',
    )


def _am_id(am_id: Optional[str]) -> Component:
    return html.Div(
        [
            html.Label('CID de l\'arrêté ministériel', htmlFor=_AM_ID),
            dcc.Input(value=am_id, id=_AM_ID, className='form-control'),
        ],
        className='col-md-12',
    )


def _diff(am_id: str, date_before: date, date_after: date) -> Component:
    am_before = extract_legifrance_am(am_id, date_before)
    am_after = extract_legifrance_am(am_id, date_after)
    diff = compute_am_diff(am_before, am_after, False)
    return diff_component(diff, 'Version de référence', 'Version comparée')


def _form(am_id: Optional[str], date_before_str: Optional[str], date_after_str: Optional[str]) -> Component:
    date_before = date.fromisoformat(date_before_str) if date_before_str else None
    date_after = date.fromisoformat(date_after_str) if date_after_str else None
    margin = {'margin-top': '10px', 'margin-bottom': '10px'}
    return html.Div(
        [
            _am_id(am_id),
            _before_date(date_before),
            _after_date(date_after),
            html.Div(id=_FORM_OUTPUT, style=margin, className='col-md-12'),
            html.Div(html.Button('Valider', className='btn btn-primary', id=_SUBMIT), className='col-12', style=margin),
        ],
        className='row g-3',
    )


def _safe_handle_submit(am_id: Optional[str], date_before: Optional[str], date_after: Optional[str]) -> Component:
    if not date_before or not date_after:
        raise _FormError('Les deux dates doivent être définies.')
    if not am_id:
        raise _FormError('Le CID de l\'arrêté doit être renseigné.')
    return _diff(am_id, date.fromisoformat(date_before), date.fromisoformat(date_after))


def _callbacks(app: Dash) -> None:
    @app.callback(
        Output(_FORM_OUTPUT, 'children'),
        Output(_DIFF, 'children'),
        Input(_SUBMIT, 'n_clicks'),
        State(_AM_ID, 'value'),
        State(_DATE_BEFORE, 'value'),
        State(_DATE_AFTER, 'value'),
    )
    def _handle_sumbit(n_clicks, am_id, date_before, date_after) -> Tuple[Component, Component]:
        if not n_clicks:
            if not (am_id and date_before and date_after):  # parameters defined in URL
                raise PreventUpdate
        try:
            return html.Div(), _safe_handle_submit(am_id, date_before, date_after)
        except _FormError as exc:
            return error_component(f'Erreur dans le formulaire: {str(exc)}'), html.Div()
        except NoConsolidationError:
            message = (
                'Impossible de comparer deux versions de cet arrêté, la version '
                "consolidée n'existe pas sur Légifrance."
            )
            return error_component(message), html.Div()
        except LegifranceRequestError as exc:
            return error_component(f'Erreur dans l\'API Légifrance: {str(exc)}'), html.Div()
        except Exception:
            return error_component(f'Erreur inattendue:\n{traceback.format_exc()}'), html.Div()


def _go_back(am_id: Optional[str]) -> Component:
    if not am_id:
        return html.Div()
    href = f'/{Endpoint.AM}/{am_id}/{Endpoint.AM_CONTENT}'
    return dcc.Link('< Retour', href=href, className='btn btn-link')


def _layout(
    am_id: Optional[str] = None, date_before: Optional[str] = None, date_after: Optional[str] = None
) -> Component:
    return html.Div(
        [
            _go_back(am_id),
            html.H3('Comparer deux versions d\'un arrêté.'),
            _form(am_id, date_before, date_after),
            dbc.Spinner(html.Div(id=_DIFF)),
        ],
        className='container mt-3',
    )


PAGE = Page(_layout, _callbacks, False)
