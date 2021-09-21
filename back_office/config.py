import logging
import os
from configparser import ConfigParser
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Optional


def _config_filename() -> str:
    file_ = Path(__file__).parent.parent / 'config.ini'
    assert file_.exists()
    return str(file_)


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


LEGIFRANCE_CLIENT_ID = _load_from_file_or_env('legifrance.client_id')
LEGIFRANCE_CLIENT_SECRET = _load_from_file_or_env('legifrance.client_secret')
LOGIN_USERNAME = _load_from_file_or_env('login.username')
LOGIN_PASSWORD = _load_from_file_or_env('login.password')
LOGIN_SECRET_KEY = _load_from_file_or_env('login.secret_key')
SLACK_ENRICHMENT_NOTIFICATION_URL = _load_from_file_or_env('slack.enrichment_notification_url')
AIDA_URL = 'https://aida.ineris.fr/consultation_document/'
PSQL_DSN = _load_from_file_or_env('storage.psql_dsn')


class EnvironmentType(Enum):
    DEV = 'dev'
    PROD = 'prod'


def _load_environment_type() -> EnvironmentType:
    return EnvironmentType(_load_from_file_or_env('environment.type'))


ENVIRONMENT_TYPE = _load_environment_type()
