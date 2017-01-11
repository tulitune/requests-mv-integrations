import pytest
from ..resources.mockserver import run_server

from requests_mv_integrations.support import (
    TuneRequest
)

from requests.exceptions import (
    RetryError
)

def test_singleton():
    object = TuneRequest()
    object2 = TuneRequest(max_retries=2)

    assert object.session is object2.session


def test_retries_throws_error(run_server):
    obj = TuneRequest(retry_tries=1, retry_codes=[500])

    with pytest.raises(RetryError):
        obj.request('GET', "http://localhost:8998/status/500")


def test_no_retries(run_server):
    obj = TuneRequest(retry_tries=1, retry_codes=[500])

    obj.request('GET', "http://localhost:8998/status/501")