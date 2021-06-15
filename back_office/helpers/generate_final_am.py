from envinorma.models import AMMetadata
from envinorma.parametrization.am_with_versions import AMWithVersions, generate_am_with_versions

from back_office.utils import DATA_FETCHER


def generate_final_am(metadata: AMMetadata) -> AMWithVersions:
    cid = metadata.cid
    return generate_am_with_versions(
        DATA_FETCHER.safe_load_most_advanced_am(cid), DATA_FETCHER.load_or_init_parametrization(cid), metadata
    )
