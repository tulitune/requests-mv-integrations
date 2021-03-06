#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  @copyright 2016 TUNE, Inc. (http://www.tune.com)
#  @namespace tune_mv_integration

import copy
import datetime as dt
import json
import logging
import os
import time
import urllib.parse
from functools import partial

import bs4
import requests
import requests_toolbelt
import xmltodict
from logging_mv_integrations import (
    TuneLoggingFormat,
    TuneLoggingHandler,
    get_logger,
)
from pprintpp import pprint
from pyhttpstatus_utils import (
    HttpStatusCode,
    HttpStatusType,
    http_status_code_to_desc,
    http_status_code_to_type,
    is_http_status_type,
    is_http_status_successful,
)
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from requests_mv_integrations import (__python_required_version__,)
from requests_mv_integrations.errors import (
    get_exception_message,
    TuneRequestErrorCodes,
)
from requests_mv_integrations.exceptions import (TuneRequestModuleError,)
from requests_mv_integrations.support.utils import (
    convert_size,
    base_class_name,
    python_check_version,
)
from requests_mv_integrations.support.safe_cast import (
    safe_int,
    safe_str,
)
from .parse import (requests_response_text_html)

log = logging.getLogger(__name__)

python_check_version(__python_required_version__)


def validate_response(
    response,
    request_curl,
    request_label=None,
):
    """Validate response

    Args:
        response:
        request_label:
        request_url:

    Returns:

    """
    response_extra = {}
    if request_label:
        response_extra.update({'request_label': request_label})

    if not response:
        log.error("Validate Response: Failed: None", extra=response_extra)

        raise TuneRequestModuleError(
            error_message="Validate Response: Failed: None",
            error_request_curl=request_curl,
            error_code=TuneRequestErrorCodes.REQ_ERR_SOFTWARE
        )
    else:
        log.debug("Validate Response: Defined", extra=response_extra)

    response_extra.update({'http_status_code': response.status_code})

    if hasattr(response, 'text'):
        response_text_length = len(response.text)
        response_extra.update({'response_text_length': response_text_length})

    if response.headers:
        if 'Content-Type' in response.headers:
            response_headers_content_type = \
                safe_str(response.headers['Content-Type'])
            response_extra.update({'Content-Type': response_headers_content_type})

        if 'Content-Length' in response.headers:
            response_headers_content_length = \
                safe_int(response.headers['Content-Length'])
            response_extra.update({'Content-Length': convert_size(response_headers_content_length)})

        if 'Content-Encoding' in response.headers:
            response_content_encoding = \
                safe_str(response.headers['Content-Encoding'])
            response_extra.update({'Content-Encoding': response_content_encoding})

        if 'Transfer-Encoding' in response.headers:
            response_transfer_encoding = \
                safe_str(response.headers['Transfer-Encoding'])
            response_extra.update({'Transfer-Encoding': response_transfer_encoding})

    if not is_http_status_successful(http_status_code=response.status_code):
        log.error("Validate Response: Failed", extra=response_extra)

        raise TuneRequestModuleError(
            error_message="Validate Request: Failed",
            error_request_curl=request_curl,
            error_code=TuneRequestErrorCodes.REQ_ERR_SOFTWARE
        )
    else:
        log.debug("Validate Response: Success", extra=response_extra)


def validate_json_response(
    response,
    request_curl,
    request_label=None,
    response_content_type_expected='application/json',
    raise_ex_if_not_json_response=True
):
    """Validate JSON response.

    Args:
        response:
        request_label:
        response_content_type_expected:
        raise_ex_if_not_json_response:

    Returns:

    """
    validate_response(response, request_label)

    json_response = None
    response_extra = {}
    if request_label:
        response_extra.update({'request_label': request_label})

    response_extra.update({'Content-Type (Expected)': response_content_type_expected})

    if hasattr(response, 'headers'):
        response_content_type = response.headers.get('Content-Type', None)

    if response_content_type is not None:
        is_valid_response_content_type = \
            response_content_type == response_content_type_expected or \
            response_content_type.startswith(response_content_type_expected)

        if is_valid_response_content_type:
            json_response = requests_response_json(
                response=response,
                request_curl=request_curl,
                request_label=request_label,
            )
        elif response_content_type.startswith('text/html'):
            try:
                response_content_html_lines = \
                    requests_response_text_html(
                        response=response
                    )
            except Exception as ex:
                raise TuneRequestModuleError(
                    error_message=request_label,
                    errors=ex,
                    error_request_curl=request_curl,
                    error_code=TuneRequestErrorCodes.REQ_ERR_UNEXPECTED_CONTENT_TYPE_RETURNED
                )

            raise TuneRequestModuleError(
                error_message="Unexpected 'Content-Type': '{}', Expected: '{}'".format(
                    response_content_type, response_content_type_expected
                ),
                errors=response_content_html_lines,
                error_request_curl=request_curl,
                error_code=TuneRequestErrorCodes.REQ_ERR_UNEXPECTED_CONTENT_TYPE_RETURNED
            )
        else:
            raise TuneRequestModuleError(
                error_message="Unexpected 'Content-Type': '{}', Expected: '{}'".format(
                    response_content_type, response_content_type_expected
                ),
                error_request_curl=request_curl,
                error_code=TuneRequestErrorCodes.REQ_ERR_UNEXPECTED_CONTENT_TYPE_RETURNED
            )
    else:
        raise TuneRequestModuleError(
            error_message="Undefined 'Content-Type'",
            error_request_curl=request_curl,
            error_code=TuneRequestErrorCodes.REQ_ERR_UNEXPECTED_CONTENT_TYPE_RETURNED
        )

    response_extra.update({
        'http_status_code': response.status_code,
        'raise_ex_if_not_json_response': raise_ex_if_not_json_response
    })

    log.debug("Validate JSON Response: Details", extra=response_extra)

    return json_response


def requests_response_json(
    response,
    request_curl,
    request_label=None,
    raise_ex_if_not_json_response=True,
):
    """Get JSON from response from requests

    Args:
        response:
        request_label:

    Returns:

    """
    json_response = None
    response_extra = {}
    if request_label:
        response_extra.update({'request_label': request_label})

    try:
        json_response = response.json()
        response_details_source = 'json'
        response_content_length = len(json_response)

        response_extra.update({
            'response_details_source': response_details_source,
            'response_content_length': response_content_length
        })
    except json.decoder.JSONDecodeError as json_decode_ex:
        log.error("Validate JSON Response: Failed: JSONDecodeError", extra=response_extra)

        data = requests_toolbelt.utils.dump.dump_all(response)
        pprint(data.decode('utf-8'))

        pprint(response.text)

        handle_json_decode_error(
            response_decode_ex=json_decode_ex,
            response=response,
            response_extra=response_extra,
            request_label=request_label,
            request_curl=request_curl
        )

    except Exception as ex:
        log.error("Validate JSON Response: Failed: Exception", extra=response_extra)

        pprint(response.text)

        handle_json_decode_error(
            response_decode_ex=ex,
            response=response,
            response_extra=response_extra,
            request_label=request_label,
            request_curl=request_curl
        )

    if json_response is None:
        if raise_ex_if_not_json_response:
            log.error("Validate JSON Response: Failed: None", extra=response_extra)

            raise TuneRequestModuleError(
                error_message="Validate JSON Response: Failed: None",
                error_request_curl=request_curl,
                error_code=TuneRequestErrorCodes.REQ_ERR_SOFTWARE
            )
        else:
            log.warning("Validate JSON Response: None", extra=response_extra)
    else:
        log.debug("Validate JSON Response: Valid", extra=response_extra)

    return json_response


def build_response_error_details(request_label, request_url, response):
    """Build gather status of Requests' response.

    Args:
        request_url:
        response:
        response_verbose:

    Returns:

    """
    http_status_code = \
        response.status_code
    http_status_type = \
        http_status_code_to_type(http_status_code)
    http_status_desc = \
        http_status_code_to_desc(http_status_code)

    response_status = "{}: {}: {}".format(http_status_code, http_status_type, http_status_desc)

    response_error_details = {
        'request_url': request_url,
        'request_label': request_label,
        'response_status': response_status,
        'response_status_code': http_status_code,
        'response_status_type': http_status_type,
        'response_status_desc': http_status_desc
    }

    if response.headers:
        if 'Content-Type' in response.headers:
            response_headers_content_type = \
                safe_str(response.headers['Content-Type'])
            response_error_details.update({'Content-Type': response_headers_content_type})

        if 'Content-Length' in response.headers and \
                response.headers['Content-Length']:
            response_headers_content_length = \
                safe_int(response.headers['Content-Length'])
            response_error_details.update({'Content-Length': response_headers_content_length})

        if 'Transfer-Encoding' in response.headers and \
                response.headers['Transfer-Encoding']:
            response_headers_transfer_encoding = \
                safe_str(response.headers['Transfer-Encoding'])
            response_error_details.update({'Transfer-Encoding': response_headers_transfer_encoding})

        if 'Content-Encoding' in response.headers and \
                response.headers['Content-Encoding']:
            response_headers_content_encoding = \
                safe_str(response.headers['Content-Encoding'])
            response_error_details.update({'Content-Encoding': response_headers_content_encoding})

    if hasattr(response, "reason") and response.reason:
        response_error_details.update({'response_reason': response.reason})

    response_details = None
    response_details_source = None

    try:
        response_details = response.json()
        response_details_source = 'json'
    except Exception:
        if hasattr(response, 'text') and \
                response.text and \
                        len(response.text) > 0:
            response_details = response.text
            response_details_source = 'text'

            if response_details.startswith('<html'):
                response_details_source = 'html'
                soup_html = bs4.BeautifulSoup(response_details, "html.parser")
                # kill all script and style elements
                for script in soup_html(["script", "style"]):
                    script.extract()  # rip it out
                text_html = soup_html.get_text()
                lines_html = [line for line in text_html.split('\n') if line.strip() != '']
                lines_html = [line.strip(' ') for line in lines_html]
                response_details = lines_html

            elif response_details.startswith('<?xml'):
                response_details_source = 'xml'
                response_details = json.dumps(xmltodict.parse(response_details))

    response_error_details.update({
        'response_details': response_details,
        'response_details_source': response_details_source
    })

    # pprint(response_error_details)

    return response_error_details


def handle_json_decode_error(
    response_decode_ex,
    response,
    response_extra=None,
    request_label=None,
    request_curl=None,
):
    """Handle JSON Decode Error

    Args:
        response_json_decode_error:
        response:
        response_extra:
        request_label:

    Returns:

    """
    if response_extra is None:
        response_extra = {}

    if request_label:
        response_extra.update({'request_label': request_label})

    if hasattr(response, 'text') and \
            response.text and \
                    len(response.text) > 0:
        response_details = response.text
        response_details_source = 'text'
        response_content_length = len(response_details)

        if response_details.startswith('<html'):
            response_details_source = 'html'
            soup_html = bs4.BeautifulSoup(response_details, "html.parser")
            # kill all script and style elements
            for script in soup_html(["script", "style"]):
                script.extract()  # rip it out
            text_html = soup_html.get_text()
            lines_html = [line for line in text_html.split('\n') if line.strip() != '']
            lines_html = [line.strip(' ') for line in lines_html]
            response_details = lines_html

        elif response_details.startswith('<?xml'):
            response_details_source = 'xml'
            response_details = json.dumps(xmltodict.parse(response_details))
        else:
            pprint(response_details)

        response_extra.update({
            'response_details': response_details,
            'response_details_source': response_details_source,
            'response_content_length': response_content_length,
            'error_exception': base_class_name(response_decode_ex),
            'error_details': get_exception_message(response_decode_ex)
        })

    log.error("Validate JSON Response: Failed: Invalid", extra=response_extra)

    raise TuneRequestModuleError(
        error_message="Validate JSON Response: Failed: Invalid",
        errors=response_decode_ex,
        error_request_curl=request_curl,
        error_code=TuneRequestErrorCodes.REQ_ERR_SOFTWARE
    )
