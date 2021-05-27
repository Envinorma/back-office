from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional, Tuple

import dash
from werkzeug.routing import Map, MapAdapter, Rule


def build_am_page(am_id: str) -> str:
    return '/edit_am/' + am_id


class Endpoint(Enum):
    INDEX = ''
    COMPARE = 'compare'
    AM = 'am'
    EDIT_AM = 'edit_am'
    DELETE_AM = 'delete_am'
    CREATE_AM = 'create_am'
    LOGIN = 'login'
    LOGOUT = 'logout'
    REGULATION_ENGINE = 'regulation_engine'

    def __repr__(self):
        return self.value

    def __str__(self):
        return self.value


ROUTER: MapAdapter = Map(
    [
        Rule(f'/{Endpoint.INDEX}', endpoint=Endpoint.INDEX),
        Rule(f'/{Endpoint.COMPARE}', endpoint=Endpoint.COMPARE),
        Rule(f'/{Endpoint.COMPARE}/id/<am_id>', endpoint=Endpoint.COMPARE),
        Rule(f'/{Endpoint.COMPARE}/id/<am_id>/<date_before>/<date_after>', endpoint=Endpoint.COMPARE),
        Rule(f'/{Endpoint.AM}/<am_id>', endpoint=Endpoint.AM),
        Rule(f'/{Endpoint.AM}/<am_id>/compare/<compare_with>', endpoint=Endpoint.AM),
        Rule(f'/{Endpoint.LOGIN}', endpoint=Endpoint.LOGIN),
        Rule(f'/{Endpoint.LOGOUT}', endpoint=Endpoint.LOGOUT),
        Rule(f'/{Endpoint.DELETE_AM}/<am_id>', endpoint=Endpoint.DELETE_AM),
        Rule(f'/{Endpoint.CREATE_AM}', endpoint=Endpoint.CREATE_AM),
        Rule(f'/{Endpoint.CREATE_AM}/<am_id>', endpoint=Endpoint.CREATE_AM),
        Rule(f'/{Endpoint.REGULATION_ENGINE}', endpoint=Endpoint.REGULATION_ENGINE),
        # Rule('/edit_am/id/<id>/operation/<operation>', endpoint=Endpoint.EDIT_AM),
    ]
).bind('')


@dataclass
class Page:
    layout: Callable[..., Any]
    callbacks_adder: Optional[Callable[[dash.Dash], None]]
