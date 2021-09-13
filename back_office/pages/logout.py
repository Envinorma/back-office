import dash_core_components as dcc
from dash.development.base_component import Component
from flask_login import logout_user

from back_office.helpers.login import get_current_user
from back_office.routing import Page


def _layout() -> Component:
    if get_current_user().is_authenticated:
        logout_user()
    return dcc.Location(pathname='/', id='back_home')


PAGE = Page(_layout, None, False)
