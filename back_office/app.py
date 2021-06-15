import os
from typing import Dict, Optional

import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from dash.development.base_component import Component
from flask_login import LoginManager
from werkzeug.exceptions import NotFound

from back_office.app_init import app
from back_office.config import AM_DATA_FOLDER, LOGIN_SECRET_KEY
from back_office.pages.am import PAGE as am_page
from back_office.pages.compare import PAGE as compare_page
from back_office.pages.create_am import PAGE as create_am_page
from back_office.pages.delete_am import PAGE as delete_am_page
from back_office.pages.edit_am.edit_am import router as edit_am_page_router
from back_office.pages.index import PAGE as index_page
from back_office.pages.login import PAGE as login_page
from back_office.pages.logout import PAGE as logout_page
from back_office.pages.regulation_engine import PAGE as regulation_engine_page
from back_office.routing import ROUTER, Endpoint, Page
from back_office.utils import UNIQUE_USER, get_current_user, split_route


def _create_tmp_am_folder():
    if not os.path.exists(AM_DATA_FOLDER):
        os.mkdir(AM_DATA_FOLDER)
    parametric_folder = f'{AM_DATA_FOLDER}/parametric_texts'
    if not os.path.exists(parametric_folder):
        os.mkdir(parametric_folder)


_create_tmp_am_folder()


def _header_link(content: str, href: str, target: Optional[str] = None, hidden: bool = False) -> Component:
    style = {'color': 'grey', 'display': 'inline-block'}
    return html.Span(html.A(content, href=href, className='nav-link', style=style, target=target), hidden=hidden)


def _get_nav() -> Component:
    guide_url = 'https://www.notion.so/Guide-d-enrichissement-3874408245dc474ca8181a3d1d50f78e'
    nav = html.Span(
        [
            _header_link('Liste des arrêtés', href='/'),
            _header_link('Guide d\'enrichissement', href=guide_url, target='_blank'),
            _header_link('Historique Légifrance', href='/compare/id/JORFTEXT000034429274/2020-01-20/2021-02-20'),
            _header_link('Se déconnecter', href=f'/{Endpoint.LOGOUT}', hidden=not get_current_user().is_authenticated),
        ],
        style={'display': 'inline-block'},
    )
    return nav


def _get_page_heading() -> Component:
    src = '/assets/logo-envinorma.png'
    sticky_style = {
        'padding': '.2em',
        'border-bottom': '1px solid rgba(0,0,0,.1)',
        'position': 'sticky',
        'top': 0,
        'background-color': '#fff',
        'z-index': '10',
        'margin-bottom': '10px',
    }
    img = html.Img(src=src, style={'width': '30px', 'display': 'inline-block'})
    return html.Div(html.Div([dcc.Link(img, href='/'), _get_nav()], className='container'), style=sticky_style)


_ENDPOINT_TO_PAGE: Dict[str, Page] = {
    Endpoint.COMPARE.value: compare_page,
    Endpoint.AM.value: am_page,
    Endpoint.LOGIN.value: login_page,
    Endpoint.LOGOUT.value: logout_page,
    Endpoint.INDEX.value: index_page,
    Endpoint.DELETE_AM.value: delete_am_page,
    Endpoint.CREATE_AM.value: create_am_page,
    Endpoint.REGULATION_ENGINE.value: regulation_engine_page,
}


def _route(pathname: str) -> Component:
    endpoint, kwargs = ROUTER.match(pathname)
    return _ENDPOINT_TO_PAGE[endpoint].layout(**kwargs)


def router(pathname: str) -> Component:
    if not pathname.startswith('/'):
        raise ValueError(f'Expecting pathname to start with /, received {pathname}')
    prefix, suffix = split_route(pathname)
    if prefix == '/edit_am':
        if not get_current_user().is_authenticated:
            return dcc.Location(pathname='/login', id='login-redirect')
        return edit_am_page_router(prefix, suffix)
    try:
        return _route(pathname)
    except NotFound:
        return html.H3('404 error: Unknown path {}'.format(pathname))


@app.callback(Output('page-content', 'children'), [Input('url', 'pathname')])
def display_page(pathname: str):
    return html.Div([_get_page_heading(), html.Div(router(pathname), className='container')])


for _page in _ENDPOINT_TO_PAGE.values():
    if _page.callbacks_adder:
        _page.callbacks_adder(app)

login_manager = LoginManager()
login_manager.init_app(app.server)
login_manager.login_view = '/login'  # type: ignore
app.server.secret_key = LOGIN_SECRET_KEY


@login_manager.user_loader
def load_user(_):
    return UNIQUE_USER


app.layout = html.Div(
    [dcc.Location(id='url', refresh=False), html.Div(id='page-content')],
    id='layout',
)

APP = app.server  # for gunicorn deployment

if __name__ == '__main__':
    app.run_server(debug=True)
