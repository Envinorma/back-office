from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional

import dash
from werkzeug.routing import Map, MapAdapter, Rule


def build_am_page(am_id: str) -> str:
    return '/edit_am/' + am_id


class Endpoint(Enum):
    INDEX = ''
    AM = 'am'
    AM_OLD = 'am_old'
    AM_COMPARE = 'am_compare'
    LEGIFRANCE_COMPARE = 'compare'
    EDIT_AM = 'edit_am'
    EDIT_AM_CONTENT = 'edit_am_content'
    DELETE_AM = 'delete_am'
    CREATE_AM = 'create_am'
    LOGIN = 'login'
    LOGOUT = 'logout'
    EDIT_TOPICS = 'edit_topics'
    REGULATION_ENGINE = 'regulation_engine'
    TOPIC_DETECTOR = 'topic_detector'

    def __repr__(self):
        return self.value

    def __str__(self):
        return self.value


ROUTER: MapAdapter = Map(
    [
        Rule(f'/{Endpoint.INDEX}', endpoint=Endpoint.INDEX.value),
        Rule(f'/{Endpoint.LEGIFRANCE_COMPARE}', endpoint=Endpoint.LEGIFRANCE_COMPARE.value),
        Rule(f'/{Endpoint.LEGIFRANCE_COMPARE}/id/<am_id>', endpoint=Endpoint.LEGIFRANCE_COMPARE.value),
        Rule(
            f'/{Endpoint.LEGIFRANCE_COMPARE}/id/<am_id>/<date_before>/<date_after>',
            endpoint=Endpoint.LEGIFRANCE_COMPARE.value,
        ),
        Rule(f'/{Endpoint.AM}/<am_id>', endpoint=Endpoint.AM.value),
        Rule(f'/{Endpoint.AM}/<am_id>/<tab>', endpoint=Endpoint.AM.value),
        Rule(f'/{Endpoint.AM_COMPARE}/<am_id>/<compare_with>', endpoint=Endpoint.AM_COMPARE.value),
        Rule(f'/{Endpoint.AM_COMPARE}/<am_id>/<compare_with>/<normalize>', endpoint=Endpoint.AM_COMPARE.value),
        Rule(f'/{Endpoint.LOGIN}', endpoint=Endpoint.LOGIN.value),
        Rule(f'/{Endpoint.LOGIN}/<origin>', endpoint=Endpoint.LOGIN.value),
        Rule(f'/{Endpoint.LOGOUT}', endpoint=Endpoint.LOGOUT.value),
        Rule(f'/{Endpoint.DELETE_AM}/<am_id>', endpoint=Endpoint.DELETE_AM.value),
        Rule(f'/{Endpoint.CREATE_AM}', endpoint=Endpoint.CREATE_AM.value),
        Rule(f'/{Endpoint.CREATE_AM}/<am_id>', endpoint=Endpoint.CREATE_AM.value),
        Rule(f'/{Endpoint.EDIT_TOPICS}/<am_id>', endpoint=Endpoint.EDIT_TOPICS.value),
        Rule(f'/{Endpoint.EDIT_AM_CONTENT}/<am_id>', endpoint=Endpoint.EDIT_AM_CONTENT.value),
        Rule(f'/{Endpoint.EDIT_AM_CONTENT}/<am_id>/<with_buttons>', endpoint=Endpoint.EDIT_AM_CONTENT.value),
        Rule(f'/{Endpoint.REGULATION_ENGINE}', endpoint=Endpoint.REGULATION_ENGINE.value),
        Rule(f'/{Endpoint.TOPIC_DETECTOR}', endpoint=Endpoint.TOPIC_DETECTOR.value),
        # Rule('/edit_am/id/<id>/operation/<operation>', endpoint=Endpoint.EDIT_AM),
    ]
).bind('')


@dataclass
class Page:
    layout: Callable[..., Any]
    callbacks_adder: Optional[Callable[[dash.Dash], None]]
