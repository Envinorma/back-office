import dash
import dash_bootstrap_components as dbc


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
            favicon=kwargs['favicon'],
            css=kwargs['css'],
            app_entry=kwargs['app_entry'],
            config=kwargs['config'],
            scripts=kwargs['scripts'],
            renderer=kwargs['renderer'],
        )


app = SVGFaviconDash(
    __name__,
    # For offline dev
    # external_stylesheets=[
    #     __file__.replace('app_init.py', 'assets/bootstrap.css'),
    #     __file__.replace('app_init.py', 'assets/style.css'),
    # ],
    external_stylesheets=[dbc.themes.BOOTSTRAP, __file__.replace('app_init.py', 'assets/style.css')],
    suppress_callback_exceptions=True,
    title='Back office - Envinorma',
    update_title=None,
)
