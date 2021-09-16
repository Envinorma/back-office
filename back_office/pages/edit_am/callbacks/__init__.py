from dash import Dash

from . import aida_legifrance_callback, diff_modal_callback, save_callback, save_modal_callback, toc_callback


def add_callbacks(app: Dash) -> None:
    toc_callback.add_callbacks(app)
    aida_legifrance_callback.add_callbacks(app)
    save_callback.add_callbacks(app)
    diff_modal_callback.add_callbacks(app)
    save_modal_callback.add_callbacks(app)
