import json
import os
from typing import Dict, Optional

from envinorma.models import AMMetadata
from envinorma.parametrization.am_with_versions import AMVersions, AMWithVersions, generate_am_with_versions
from envinorma.parametrization.apply_parameter_values import AMWithApplicability

from back_office.config import create_folder_and_generate_parametric_filename, get_parametric_ams_folder
from back_office.utils import DATA_FETCHER, ensure_not_none, write_json


def _generate_final_am(metadata: AMMetadata) -> AMWithVersions:
    cid = metadata.cid
    return generate_am_with_versions(
        DATA_FETCHER.safe_load_most_advanced_am(cid), DATA_FETCHER.load_or_init_parametrization(cid), metadata
    )


def _flush_folder(am_id: str) -> None:
    folder = get_parametric_ams_folder(am_id)
    if os.path.exists(folder):
        for file_ in os.listdir(folder):
            os.remove(os.path.join(folder, file_))


def _dump_am_versions(am_id: str, versions: Optional[AMVersions]) -> None:
    if not versions:
        return
    _flush_folder(am_id)
    for version_desc, version in versions.items():
        filename = create_folder_and_generate_parametric_filename(am_id, version_desc)
        write_json(version.to_dict(), filename)


def generate_and_dump_am_version(am_id: str) -> None:
    final_am = _generate_final_am(ensure_not_none(DATA_FETCHER.load_am_metadata(am_id)))
    _dump_am_versions(am_id, final_am.am_versions)


def _create_if_inexistent(folder: str) -> None:
    if not os.path.exists(folder):
        os.mkdir(folder)


def _load_am(path: str) -> AMWithApplicability:
    return AMWithApplicability.from_dict(json.load(open(path)))


def _load_parametric_ams(folder: str) -> Dict[str, AMWithApplicability]:
    return {file_: _load_am(os.path.join(folder, file_)) for file_ in os.listdir(folder)}


def _generate_versions(am_id: str, folder: str, regenerate: bool) -> None:
    if not regenerate and os.listdir(folder):
        return
    generate_and_dump_am_version(am_id)


def load_am_versions(am_id: str, regenerate: bool) -> Dict[str, AMWithApplicability]:
    folder = get_parametric_ams_folder(am_id)
    _create_if_inexistent(folder)
    _generate_versions(am_id, folder, regenerate)
    return _load_parametric_ams(folder)
