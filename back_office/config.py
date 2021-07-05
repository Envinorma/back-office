import logging
import os
from configparser import ConfigParser
from enum import Enum
from functools import lru_cache
from typing import Optional, Tuple


def _config_filename() -> str:
    filename = __file__.replace('back_office/config.py', 'config.ini')
    assert 'config.ini' in filename
    return filename


@lru_cache
def _load_config_file() -> ConfigParser:
    parser = ConfigParser()
    filename = _config_filename()
    if os.path.exists(filename):
        parser.read(filename)
    else:
        logging.warn('config.ini not found, reading config from env')
    return parser


def _load_from_file(key: str) -> Optional[str]:
    first_order_key, second_order_key = key.split('.')
    try:
        return _load_config_file()[first_order_key][second_order_key]
    except KeyError:
        return None


def _load_from_env(key: str) -> Optional[str]:
    return os.environ.get(key.replace('.', '_').upper())


def _load_from_file_or_env(key: str) -> str:
    candidate = _load_from_file(key) or _load_from_env(key)
    if not candidate:
        raise ValueError(f'Environment variable {key} is not set.')
    return candidate


def get_parametric_ams_folder(am_id: str) -> str:
    return f'{AM_DATA_FOLDER}/parametric_texts/{am_id}'


def generate_parametric_descriptor(version_descriptor: Tuple[str, ...]) -> str:
    if not version_descriptor:
        return 'no_date_version'
    return '_AND_'.join(version_descriptor).replace(' ', '_')


def create_folder_and_generate_parametric_filename(am_id: str, version_descriptor: Tuple[str, ...]) -> str:
    folder_name = get_parametric_ams_folder(am_id)
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    return get_parametric_ams_folder(am_id) + '/' + generate_parametric_descriptor(version_descriptor) + '.json'


LEGIFRANCE_CLIENT_ID = _load_from_file_or_env('legifrance.client_id')
LEGIFRANCE_CLIENT_SECRET = _load_from_file_or_env('legifrance.client_secret')
LOGIN_USERNAME = _load_from_file_or_env('login.username')
LOGIN_PASSWORD = _load_from_file_or_env('login.password')
LOGIN_SECRET_KEY = _load_from_file_or_env('login.secret_key')
SLACK_ENRICHMENT_NOTIFICATION_URL = _load_from_file_or_env('slack.enrichment_notification_url')
AIDA_URL = 'https://aida.ineris.fr/consultation_document/'
AM_DATA_FOLDER = _load_from_file_or_env('storage.am_data_folder')
PSQL_DSN = _load_from_file_or_env('storage.psql_dsn')


class EnvironmentType(Enum):
    DEV = 'dev'
    PROD = 'prod'


def _load_environment_type() -> EnvironmentType:
    return EnvironmentType(_load_from_file_or_env('environment.type'))


ENVIRONMENT_TYPE = _load_environment_type()
