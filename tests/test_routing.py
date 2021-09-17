from back_office.app import _ENDPOINT_TO_PAGE
from back_office.routing import ROUTER, Endpoint


def test_routing():
    """
    each rule in ROUTER must be tied to a python file with a layout function and expected arguments
    """
    for rule in ROUTER.map.iter_rules():
        for arg in rule.arguments:
            page = _ENDPOINT_TO_PAGE.get(Endpoint(rule.endpoint))
            assert page, f"{rule.endpoint} is not mapped to a page"
            assert arg in page.layout.__annotations__
