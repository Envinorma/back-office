from dash import dcc, html
from dash.development.base_component import Component

from back_office.helpers.login import get_current_user
from back_office.routing import Endpoint


def _header_link(content: str, href: str, hidden: bool = False, left: bool = False) -> Component:
    base_class_name = 'btn btn-link header-link'
    class_name = base_class_name + (' float-end' if left else '')
    return html.Span(dcc.Link(content, href=href, className=class_name), hidden=hidden)


def _nav() -> Component:
    user_not_auth = not get_current_user().is_authenticated
    nav = html.Span(
        [
            _header_link('Liste des arrêtés', href='/'),
            _header_link('Exportation des AMs', href=f'/{Endpoint.UPLOAD_AMS}', hidden=user_not_auth),
            _header_link("S'identifier", href=f'/{Endpoint.LOGIN}', hidden=not user_not_auth, left=True),
            _header_link('Se déconnecter', href=f'/{Endpoint.LOGOUT}', hidden=user_not_auth, left=True),
        ],
    )
    return nav


def header() -> Component:
    src = '/assets/logo-envinorma-grey.svg'
    sticky_style = {
        'padding': '.2em',
        'border-bottom': '1px solid rgba(0,0,0,.1)',
        'position': 'sticky',
        'top': 0,
        'background-color': '#1D2026',
        'z-index': '10',
    }
    img = html.Img(src=src, style={'width': '30px', 'display': 'inline-block'})
    return html.Div(html.Div([dcc.Link(img, href='/'), _nav()], className='container-fluid'), style=sticky_style)
