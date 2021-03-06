import os
from configparser import ConfigParser
from pathlib import Path

_CONFIG_FILE = Path(__file__).parent.parent / 'config.ini'
_CONFIG_TEMPLATE_FILE = Path(__file__).parent.parent / 'config_template.ini'


def assert_no_missing_parameter_in_template():
    config = ConfigParser()
    config.read(_CONFIG_FILE)
    config_template = ConfigParser()
    config_template.read(_CONFIG_TEMPLATE_FILE)
    for section in config.sections():
        for var in config[section]:
            assert var in config_template[section]


def test_config():
    if os.path.exists(_CONFIG_FILE):
        assert_no_missing_parameter_in_template()
