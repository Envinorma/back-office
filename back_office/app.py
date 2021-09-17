from typing import Any, Dict, Mapping, Tuple
from urllib.parse import quote_plus

from dash import Input, Output, dcc, html
from dash.development.base_component import Component

from flask.app import Flask
from flask_login import LoginManager
from werkzeug.exceptions import NotFound

from back_office.app_init import app
from back_office.components.header import header
from back_office.config import LOGIN_SECRET_KEY
from back_office.helpers.login import UNIQUE_USER, get_current_user
from back_office.pages.am import PAGE as am_page
from back_office.pages.create_am import PAGE as create_am_page
from back_office.pages.delete_am import PAGE as delete_am_page
from back_office.pages.edit_am import PAGE as edit_am_page
from back_office.pages.edit_am_content import PAGE as edit_am_content_page
from back_office.pages.edit_parametrization import PAGE as edit_parametrization_page
from back_office.pages.edit_topics import PAGE as edit_topics_page
from back_office.pages.envinorma_compare import PAGE as envinorma_compare_page
from back_office.pages.index import PAGE as index_page
from back_office.pages.legifrance_compare import PAGE as legifrance_compare_page
from back_office.pages.login import PAGE as login_page
from back_office.pages.logout import PAGE as logout_page
from back_office.pages.edit_parameter_element import PAGE_ALTERNATIVE_SECTION as alternative_section_page
from back_office.pages.edit_parameter_element import PAGE_CONDITION as condition_page
from back_office.pages.edit_parameter_element import PAGE_WARNING as warning_page
from back_office.pages.regulation_engine import PAGE as regulation_engine_page
from back_office.pages.topic_detector import PAGE as topic_detector_page
from back_office.pages.upload_ams import PAGE as upload_ams_page
from back_office.pages.am_applicability import PAGE as am_applicability_page
from back_office.routing import ROUTER, Endpoint, Page
from back_office.utils import ensure_not_none

_ENDPOINT_TO_PAGE: Dict[Endpoint, Page] = {
    Endpoint.AM: am_page,
    Endpoint.LEGIFRANCE_COMPARE: legifrance_compare_page,
    Endpoint.EDIT_AM_CONTENT: edit_am_content_page,
    Endpoint.EDIT_AM: edit_am_page,
    Endpoint.EDIT_PARAMETRIZATION: edit_parametrization_page,
    Endpoint.EDIT_TOPICS: edit_topics_page,
    Endpoint.AM_COMPARE: envinorma_compare_page,
    Endpoint.LOGIN: login_page,
    Endpoint.LOGOUT: logout_page,
    Endpoint.INDEX: index_page,
    Endpoint.DELETE_AM: delete_am_page,
    Endpoint.CREATE_AM: create_am_page,
    Endpoint.REGULATION_ENGINE: regulation_engine_page,
    Endpoint.TOPIC_DETECTOR: topic_detector_page,
    Endpoint.UPLOAD_AMS: upload_ams_page,
    Endpoint.ADD_ALTERNATIVE_SECTION: alternative_section_page,
    Endpoint.ADD_INAPPLICABILITY: condition_page,
    Endpoint.ADD_WARNING: warning_page,
    Endpoint.AM_APPLICABILITY: am_applicability_page,
}


def _route(pathname: str) -> Tuple[Page, Mapping[str, Any]]:
    endpoint, kwargs = ROUTER.match(pathname)
    return (_ENDPOINT_TO_PAGE[Endpoint(endpoint)], kwargs)


def router(pathname: str) -> Component:
    if not pathname.startswith('/'):
        raise ValueError(f'Expecting pathname to start with /, received {pathname}')
    try:
        page, kwargs = _route(pathname)
    except NotFound:
        return html.H3('404 error: Unknown path {}'.format(pathname))
    if page.login_required and not get_current_user().is_authenticated:
        origin = quote_plus(pathname)
        return dcc.Location(pathname=f'/{Endpoint.LOGIN}/{origin}', id='login-redirect')
    return page.layout(**kwargs)


@app.callback(Output('page-content', 'children'), [Input('url', 'pathname')])
def display_page(pathname: str):
    return html.Div([header(), html.Div(router(pathname), className='container')])


for _page in _ENDPOINT_TO_PAGE.values():
    if _page.callbacks_adder:
        _page.callbacks_adder(app)

login_manager = LoginManager()
login_manager.init_app(app.server)
login_manager.login_view = '/login'  # type: ignore

APP: Flask = ensure_not_none(app.server)  # for gunicorn deployment

APP.secret_key = LOGIN_SECRET_KEY


@login_manager.user_loader
def load_user(_):
    return UNIQUE_USER


app.layout = html.Div([dcc.Location(id='url', refresh=False), html.Div(id='page-content')], id='layout')


if __name__ == '__main__':
    app.run_server(debug=True)
