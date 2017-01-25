#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  @copyright 2016 TUNE, Inc. (http://www.tune.com)
#  @namespace requests_mv_integration

import pytest
from requests_mv_integrations.support import (TuneRequest, Singleton)
from requests.exceptions import RetryError


def setup_function():
    Singleton._instances = {}


def test_singleton():
    request_object = TuneRequest()
    request_object2 = TuneRequest()
    assert request_object.session is request_object2.session


@pytest.mark.parametrize(
    "retry_code",
    (500, 501, 502),
)
def test_retries_throws_error(retry_code):
    obj = TuneRequest(retry_codes=[retry_code])
    with pytest.raises(RetryError):
        obj.request('GET', "http://localhost:8998/status/" + str(retry_code))


@pytest.mark.parametrize("retry_code, status", (
    (501, 500),
    (502, 503),
))
def test_no_retries(retry_code, status):
    obj = TuneRequest(retry_codes=[retry_code])
    obj.request('GET', "http://localhost:8998/status/" + str(status))
