from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import dash
from werkzeug.routing import Map, MapAdapter, Rule


class Endpoint(Enum):
    INDEX = ''
    AM = 'am'
    AM_OLD = 'am_old'
    AM_COMPARE = 'am_compare'
    LEGIFRANCE_COMPARE = 'compare'
    EDIT_PARAMETRIZATION = 'edit_parametrization'
    EDIT_AM = 'edit_am'
    EDIT_AM_CONTENT = 'edit_am_content'
    DELETE_AM = 'delete_am'
    CREATE_AM = 'create_am'
    LOGIN = 'login'
    LOGOUT = 'logout'
    EDIT_TOPICS = 'edit_topics'
    UPLOAD_AMS = 'upload_ams'
    REGULATION_ENGINE = 'regulation_engine'
    TOPIC_DETECTOR = 'topic_detector'
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
    Endpoint.AM: ['/{}/<am_id>', '/{}/<am_id>/<tab>'],
    Endpoint.AM_COMPARE: ['/{}/<am_id>/<compare_with>', '/{}/<am_id>/<compare_with>/<normalize>'],
    Endpoint.LOGIN: ['/{}', '/{}/<origin>'],
    Endpoint.LOGOUT: ['/{}'],
    Endpoint.DELETE_AM: ['/{}/<am_id>'],
    Endpoint.CREATE_AM: ['/{}', '/{}/<am_id>'],
    Endpoint.UPLOAD_AMS: ['/{}'],
    Endpoint.EDIT_TOPICS: ['/{}/<am_id>'],
    Endpoint.EDIT_PARAMETRIZATION: ['/{}/<am_id>'],
    Endpoint.EDIT_AM: ['/{}/<am_id>'],
    Endpoint.EDIT_AM_CONTENT: ['/{}/<am_id>', '/{}/<am_id>/<with_buttons>'],
    Endpoint.REGULATION_ENGINE: ['/{}'],
    Endpoint.TOPIC_DETECTOR: ['/{}'],
    Endpoint.ADD_WARNING: ['/{}/<am_id>', '/{}/<am_id>/<parameter_id>', '/{}/<am_id>/<parameter_id>/copy'],
    Endpoint.ADD_INAPPLICABILITY: ['/{}/<am_id>', '/{}/<am_id>/<parameter_id>', '/{}/<am_id>/<parameter_id>/copy'],
    Endpoint.ADD_ALTERNATIVE_SECTION: ['/{}/<am_id>', '/{}/<am_id>/<parameter_id>', '/{}/<am_id>/<parameter_id>/copy'],
    Endpoint.AM_APPLICABILITY: ['/{}/<am_id>'],
}

ROUTER: MapAdapter = Map(
    [
        Rule(route.format(endpoint), endpoint=endpoint.value)
        for endpoint, routes in _ENDPOINT_TO_ROUTES.items()
        for route in routes
    ]
).bind('')


@dataclass
class Page:
    layout: Callable[..., Any]
    callbacks_adder: Optional[Callable[[dash.Dash], None]]
    login_required: bool
