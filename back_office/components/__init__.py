from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union
from urllib.parse import quote_plus

import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.development.base_component import Component
from typing_extensions import Literal

from back_office.routing import Endpoint

from .table import ExtendedComponent  # noqa: F401


def replace_line_breaks(message: str) -> List[Union[str, Component]]:
    return [el for piece in message.split('\n') for el in [piece, html.Br()]]


def alert(message: str, color: Literal['success', 'danger', 'warning']) -> Component:
    return dbc.Alert(replace_line_breaks(message), color=color, className='mt-3 mb-3', dismissable=True)


def error_component(message: str) -> Component:
    return alert(message, 'danger')


def success_component(message: str) -> Component:
    return alert(message, 'success')


def warning_component(message: str) -> Component:
    return alert(message, 'warning')


class ButtonState(Enum):
    NORMAL = 0
    DISABLED = 1
    HIDDEN = 2
    NORMAL_LINK = 3
    NORMAL_LIGHT = 4


def button(text: str, state: ButtonState, id_: Optional[Union[str, Dict]] = None) -> html.Button:
    disabled = state not in (ButtonState.NORMAL, ButtonState.NORMAL_LINK, ButtonState.NORMAL_LIGHT)
    hidden = state == ButtonState.HIDDEN
    className = 'btn btn-primary'
    if state == ButtonState.NORMAL_LINK:
        className = 'btn btn-link'
    if state == ButtonState.NORMAL_LIGHT:
        className = 'btn btn-light'
    if id_:
        return html.Button(
            text,
            id=id_,
            disabled=disabled,
            className=className,
            n_clicks=0,
            hidden=hidden,
        )
    return html.Button(text, disabled=disabled, className=className, n_clicks=0, hidden=hidden)


def link_button(text: str, href: str, state: ButtonState) -> Component:
    if state not in (ButtonState.NORMAL, ButtonState.NORMAL_LINK):
        return button(text, state)
    return dcc.Link(button(text, state), href=href)


def surline_text(str_: str, positions_to_surline: Set[int], style: Dict[str, Any]) -> Union[Component, str]:
    if not positions_to_surline:
        return str_
    surline = False
    current_word = ''
    components: List[Union[Component, str]] = []
    for position, char in enumerate(str_):
        if position in positions_to_surline:
            if not surline:
                components.append(current_word)
                current_word = char
                surline = True
            else:
                current_word += char
        else:
            if surline:
                components.append(html.Span(current_word, style=style))
                surline = False
                current_word = char
            else:
                current_word += char
    if surline:
        components.append(html.Span(current_word, style=style))
    else:
        components.append(current_word)
    return html.Span(components)


def login_redirect(pathname: str) -> Component:
    origin = quote_plus(pathname)
    return dcc.Location(pathname=f'/{Endpoint.LOGIN}/{origin}', id='login-redirect')
