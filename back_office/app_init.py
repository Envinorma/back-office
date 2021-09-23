from pathlib import Path

import dash
import dash_bootstrap_components as dbc
import diskcache
from dash.long_callback.managers.diskcache_manager import DiskcacheLongCallbackManager


class SVGFaviconDash(dash.Dash):
    def interpolate_index(self, **kwargs):
        return '''
        <!DOCTYPE html>
        <html>
            <head>
                {metas}
                <title>{title}</title>
                <link rel="icon" type="image/svg+xml" href="/assets/favicon.svg">
                {css}
            </head>
            <body>
                {app_entry}
                <footer>
                    {config}
                    {scripts}
                    {renderer}
                </footer>
            </body>
        </html>
        '''.format(
            metas=kwargs['metas'],
            title=kwargs['title'],
            css=kwargs['css'],
            app_entry=kwargs['app_entry'],
            config=kwargs['config'],
            scripts=kwargs['scripts'],
            renderer=kwargs['renderer'],
        )


_CACHE = diskcache.Cache('/tmp')

app = SVGFaviconDash(
    __name__,
    # For offline dev
    # external_stylesheets=[
    #     Path(__file__).parent.parent / 'assets/bootstrap.css',
    #     Path(__file__).parent.parent / 'assets/style.css',
    # ],
    external_stylesheets=[dbc.themes.BOOTSTRAP, Path(__file__).parent.parent / 'assets/style.css'],
    suppress_callback_exceptions=True,
    long_callback_manager=DiskcacheLongCallbackManager(_CACHE),
    title='Back office - Envinorma',
    update_title=None,
)
