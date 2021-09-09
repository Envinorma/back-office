import json
import os
import shutil
import tempfile
from datetime import datetime
from typing import Any, Dict, List, Union

from envinorma.models.arrete_ministeriel import ArreteMinisteriel
from envinorma.models.validate_am import check_am
from envinorma.utils import typed_tqdm

from back_office.helpers.ovh import OVHClient
from back_office.utils import DATA_FETCHER


def _upload_to_ovh(local_filename: str, remote_filename: str) -> None:
    OVHClient.upload_document('am', local_filename, remote_filename)


def _dump(object_: Union[Dict, List], filename: str) -> None:
    with open(filename, 'w') as file_:
        json.dump(object_, file_, ensure_ascii=False, indent=2, sort_keys=True)


def _dump_am(am: Dict[str, Any], folder: str) -> None:
    filename = os.path.join(folder, am['id'] + '.json')
    _dump(am, filename)


def _load_ams() -> List[ArreteMinisteriel]:
    return DATA_FETCHER.build_enriched_ams()


def _dump_ams(ams: List[ArreteMinisteriel], folder: str) -> None:
    for am in typed_tqdm(ams, 'Dumping AMs'):
        _dump_am(am.to_dict(), folder)


def _check_ams(ams: List[ArreteMinisteriel]) -> None:
    for am in ams:
        check_am(am)


def _remote_filename() -> str:
    return f'ams/{datetime.now().isoformat()}.zip'


def _zip_and_upload(folder: str) -> str:
    filename = _remote_filename()
    with tempfile.NamedTemporaryFile('w', prefix='am-repo') as file_:
        shutil.make_archive(file_.name, 'zip', folder)
        _upload_to_ovh(f'{file_.name}.zip', filename)
    return filename


def upload_ams() -> str:
    ams = _load_ams()
    _check_ams(ams)
    with tempfile.TemporaryDirectory() as tmp_dir:
        _dump_ams(ams, tmp_dir)
        filename = _zip_and_upload(tmp_dir)
    return filename
