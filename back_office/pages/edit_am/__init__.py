from back_office.routing import Page

from .callbacks import add_callbacks
from .layout import layout

PAGE: Page = Page(layout, add_callbacks, login_required=True)
