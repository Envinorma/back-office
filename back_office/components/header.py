from typing import Optional

from dash import dcc, html
from dash.development.base_component import Component

from back_office.helpers.login import get_current_user
from back_office.routing import Endpoint


def _header_link(content: str, href: str, target: Optional[str] = None, hidden: bool = False) -> Component:
    style = {'display': 'inline-block'}
    return html.Span(
        html.A(content, href=href, className='nav-link', style=style, target=target),
        hidden=hidden,
        className='main-header',
    )


def _nav() -> Component:
    guide_url = 'https://www.notion.so/Guide-d-enrichissement-3874408245dc474ca8181a3d1d50f78e'
    user_not_auth = not get_current_user().is_authenticated
    nav = html.Span(
        [
            _header_link('Liste des arrêtés', href='/'),
            _header_link('Guide d\'enrichissement', href=guide_url, target='_blank'),
            _header_link(
                'Historique Légifrance',
                href=f'/{Endpoint.LEGIFRANCE_COMPARE}/id/JORFTEXT000034429274/2020-01-20/2021-02-20',
            ),
            _header_link("S'identifier", href=f'/{Endpoint.LOGIN}', hidden=not user_not_auth),
            _header_link('Exportation des AMs', href=f'/{Endpoint.UPLOAD_AMS}', hidden=user_not_auth),
            _header_link('Se déconnecter', href=f'/{Endpoint.LOGOUT}', hidden=user_not_auth),
        ],
        style={'display': 'inline-block'},
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
        'margin-bottom': '10px',
    }
    img = html.Img(src=src, style={'width': '30px', 'display': 'inline-block'})
    return html.Div(html.Div([dcc.Link(img, href='/'), _nav()], className='container'), style=sticky_style)
