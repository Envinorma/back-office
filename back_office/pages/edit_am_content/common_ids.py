import json
from typing import Tuple

import dash

AM_ID = 'edit-am-content-am-id'


def extract_id_type_and_key_from_context() -> Tuple[str, str]:
    id_ = json.loads(dash.callback_context.triggered[0]['prop_id'].split('.')[0])
    return id_['type'], id_['key']
