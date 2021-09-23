from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import dash
from werkzeug.routing import Map, MapAdapter, Rule


class Endpoint(Enum):
    INDEX = ''
    AM = 'am'
    AM_COMPARE = 'am_compare'
    LEGIFRANCE_COMPARE = 'compare'
    EDIT_AM = 'edit_am'
    DELETE_AM = 'delete_am'
    NEW_AM = 'new_am'
    AM_METADATA = 'am_metadata'
    AM_APERCU = 'apercu'
    AM_CONTENT = 'content'
    PARAMETRIZATION = 'parametrization'
    TOPICS = 'topics'
    LOGIN = 'login'
    LOGOUT = 'logout'
    EDIT_TOPICS = 'edit_topics'
    REGULATION_ENGINE = 'regulation_engine'
    ADD_WARNING = 'add_warning'
    ADD_INAPPLICABILITY = 'add_inapplicability'
    ADD_ALTERNATIVE_SECTION = 'add_alternative_section'
    AM_APPLICABILITY = 'am_applicability'

    def __repr__(self):
        return self.value

    def __str__(self):
        return self.value


_ENDPOINT_TO_ROUTES: Dict[Endpoint, List[str]] = {
    Endpoint.INDEX: ['/{}'],
    Endpoint.LEGIFRANCE_COMPARE: ['/{}', '/{}/id/<am_id>', '/{}/id/<am_id>/<date_before>/<date_after>'],
    Endpoint.AM_METADATA: [f'/{Endpoint.AM}/<am_id>' + '/{}', f'/{Endpoint.AM}/<am_id>/{"{}"}/<edit>'],
    Endpoint.AM_APERCU: [f'/{Endpoint.AM}/<am_id>'],
    Endpoint.AM_CONTENT: [f'/{Endpoint.AM}/<am_id>' + '/{}'],
    Endpoint.PARAMETRIZATION: [f'/{Endpoint.AM}/<am_id>' + '/{}'],
    Endpoint.TOPICS: [f'/{Endpoint.AM}/<am_id>' + '/{}'],
    Endpoint.AM_COMPARE: ['/{}/<am_id>/<compare_with>', '/{}/<am_id>/<compare_with>/<normalize>'],
    Endpoint.LOGIN: ['/{}', '/{}/<origin>'],
    Endpoint.LOGOUT: ['/{}'],
    Endpoint.DELETE_AM: ['/{}/<am_id>'],
    Endpoint.NEW_AM: ['/{}', '/{}/<am_id>'],
    Endpoint.EDIT_TOPICS: ['/{}/<am_id>'],
    Endpoint.EDIT_AM: ['/{}/<am_id>'],
    Endpoint.REGULATION_ENGINE: ['/{}'],
    Endpoint.ADD_WARNING: ['/{}/<am_id>', '/{}/<am_id>/<parameter_id>', '/{}/<am_id>/<parameter_id>/<copy>'],
    Endpoint.ADD_INAPPLICABILITY: ['/{}/<am_id>', '/{}/<am_id>/<parameter_id>', '/{}/<am_id>/<parameter_id>/<copy>'],
    Endpoint.ADD_ALTERNATIVE_SECTION: [
        '/{}/<am_id>',
        '/{}/<am_id>/<parameter_id>',
        '/{}/<am_id>/<parameter_id>/<copy>',
    ],
    Endpoint.AM_APPLICABILITY: ['/{}/<am_id>'],
}

ROUTER: MapAdapter = Map(
    [
        Rule(route.format(endpoint), endpoint=endpoint.value)
        for endpoint, routes in _ENDPOINT_TO_ROUTES.items()
        for route in routes
    ]
).bind('')


class Routing:
    @staticmethod
    def parametrization_path(am_id: str) -> str:
        return f'/{Endpoint.AM}/{am_id}/{Endpoint.PARAMETRIZATION}'

    @staticmethod
    def apercu_path(am_id: str) -> str:
        return f'/{Endpoint.AM}/{am_id}'

    @staticmethod
    def topics_path(am_id: str) -> str:
        return f'/{Endpoint.AM}/{am_id}/{Endpoint.TOPICS}'

    @staticmethod
    def metadata_path(am_id: str, edit: bool = False) -> str:
        prefix = f'/{Endpoint.AM}/{am_id}/{Endpoint.AM_METADATA}'
        if edit:
            return f'{prefix}/edit'
        return prefix


@dataclass
class Page:
    layout: Callable[..., Any]
    callbacks_adder: Optional[Callable[[dash.Dash], None]]
    login_required: bool
