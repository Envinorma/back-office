from dash import Dash, dcc, html
from dash.development.base_component import Component
from envinorma.models import AMMetadata


def _link(text: str, href: str) -> Component:
    return dcc.Link(html.Button(text, className='btn btn-link'), href=href)


def _diff_component(am_id: str) -> Component:
    return html.Div(
        [
            html.H2('Comparer'),
            html.Div(_link('Avec la version Légifrance', f'/am_compare/{am_id}/legifrance')),
            html.Div(_link('Avec la version AIDA', f'/am_compare/{am_id}/aida')),
            html.Div(_link('Comparer deux versions légifrance successives', f'/compare/id/{am_id}')),
        ]
    )


def _layout(am_metadata: AMMetadata) -> Component:
    return _diff_component(am_metadata.cid)


def _callbacks(app: Dash, tab_id: str) -> None:
    ...


TAB = ('Comparaisons', _layout, _callbacks)
