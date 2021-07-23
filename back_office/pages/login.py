from typing import Optional
from urllib.parse import unquote

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash import Dash, no_update
from dash.dependencies import Input, Output, State
from dash.development.base_component import Component
from flask_login import login_user

from back_office.helpers.login import UNIQUE_USER
from back_office.routing import Page
from back_office.utils import generate_id

_ORIGIN = generate_id(__file__, 'origin')
_LOGIN_URL = generate_id(__file__, 'login-url')
_LOGIN_ALERT = generate_id(__file__, 'login-alert')
_LOGIN_USERNAME = generate_id(__file__, 'login-username')
_LOGIN_PASSWORD = generate_id(__file__, 'login-password')
_LOGIN_BUTTON = generate_id(__file__, 'login-button')


def _form() -> Component:
    return dbc.FormGroup(
        [
            dbc.Input(id=_LOGIN_USERNAME, autoFocus=True),
            dbc.FormText('Nom d\'utilisateur'),
            html.Br(),
            dbc.Input(id=_LOGIN_PASSWORD, type='password', debounce=True),
            dbc.FormText('Mot de passe'),
            html.Br(),
            dbc.Button('Valider', color='primary', id=_LOGIN_BUTTON),
        ]
    )


_INFO_TEXT = (
    "L'édition d'un arrêté ministériel est faite par l'équipe Envinorma."
    " Si vous relevez une erreur sur un arrêté, n'hésitez pas à nous en faire part "
    "par email à l'adresse drieat-if.envinorma@developpement-durable.gouv.fr"
)


def _layout(origin: Optional[str] = None) -> Component:
    col = [
        html.Div(id=_LOGIN_URL),
        html.H2('Connexion'),
        dbc.Alert(_INFO_TEXT, dismissable=True),
        html.Div(id=_LOGIN_ALERT),
        dcc.Store(id=_ORIGIN, data=origin),
        _form(),
    ]
    return dbc.Row(dbc.Col(col, width=6))


def _success() -> Component:
    return dbc.Alert('Connexion réussie.', color='success', dismissable=True)


def _error() -> Component:
    return dbc.Alert("Erreur dans le nom d'utilisateur ou le mot de passe.", color='danger', dismissable=True)


def _path(origin: Optional[str]) -> str:
    if not origin:
        return '/'
    return unquote(origin)


def _callbacks(app: Dash):
    @app.callback(
        Output(_LOGIN_URL, 'children'),
        Output(_LOGIN_ALERT, 'children'),
        Input(_LOGIN_BUTTON, 'n_clicks'),
        State(_LOGIN_PASSWORD, 'value'),
        State(_LOGIN_USERNAME, 'value'),
        State(_ORIGIN, 'data'),
        prevent_initial_call=True,
    )
    def _login(n_clicks, password, username, origin):
        if n_clicks and password and username:
            if username == UNIQUE_USER.username and password == UNIQUE_USER.password:
                login_user(UNIQUE_USER)
                return dcc.Location(pathname=_path(origin), id='login-redirection'), _success()
            else:
                return no_update, _error()
        return no_update, ''


PAGE = Page(_layout, _callbacks)
