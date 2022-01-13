import json
import logging

import pytest

@pytest.fixture
def secrets():
    with open('secrets.json') as f:
        secrets = json.loads(f.read())
    return secrets


@pytest.fixture
def logger():
    l = logging.getLogger(__name__)
    l.setLevel(logging.DEBUG)
    return l
