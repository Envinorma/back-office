from functools import lru_cache
from typing import Any, Dict, Iterable, List, Literal

from swiftclient.service import SwiftService, SwiftUploadObject

BucketName = Literal['ap', 'am']


def _check_upload(results: List[Dict]) -> None:
    for result in results:
        if not result.get('success'):
            raise ValueError(f'Failed Uploading document. Response:\n{result}')


def _check_auth(service: SwiftService) -> None:
    services = list(service.list())
    if len(services) != 1:
        return
    error = services[0].get('error')
    traceback = services[0].get('traceback')
    if error:
        raise ValueError(f'Probable error in authentication: {error}\n{traceback}')
    print('OVH service successfully started.')


@lru_cache
def _get_swift_service() -> SwiftService:
    service = SwiftService()
    _check_auth(service)
    return service


class OVHClient:
    @staticmethod
    def list_bucket_object_names(bucket: BucketName) -> List[str]:
        lists = list(_get_swift_service().list(bucket))
        return [x['name'] for list_ in lists for x in list_['listing']]

    @staticmethod
    def file_exists(filename: str, bucket_name: BucketName) -> bool:
        results: List[Dict] = list(_get_swift_service().stat(bucket_name, [filename]))  # type: ignore
        return results[0]['success']

    @staticmethod
    def upload_document(bucket_name: BucketName, source: str, destination: str) -> None:
        remote = SwiftUploadObject(source, object_name=destination)
        result = list(_get_swift_service().upload(bucket_name, [remote]))
        _check_upload(result)

    @staticmethod
    def list_bucket_objects(bucket_name: BucketName) -> Iterable[Dict[str, Any]]:
        return _get_swift_service().list(bucket_name)

    @staticmethod
    def objects_name_and_sizes(bucket_name: BucketName) -> Dict[str, int]:
        batches = OVHClient.list_bucket_objects(bucket_name)
        return {element['name']: element['bytes'] for batch in batches for element in batch['listing']}
