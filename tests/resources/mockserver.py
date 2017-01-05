#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#  @copyright 2016 TUNE, Inc. (http://www.tune.com)
#  @namespace tune_mv_integration

import pytest
import os
from os import curdir, sep
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

import json
PORT = 8998


class StaticJsonFilesHandler(BaseHTTPRequestHandler):

    def do_PUT(self):
        try:
            if self.path.endswith('upload'):
                self.send_response(200)
                self.send_header("Content-Type", self.headers['Content-Type'])
                self.end_headers()
                self.wfile.write(json.dumps({"name":"avital"}))
                return

        except IOError:
            self.send_error(404, 'File Not Found: %s' % self.path)


@pytest.fixture(scope='module')
def run_server(server_class=HTTPServer, handler_class=StaticJsonFilesHandler):
    try:
        server_address = ('localhost', PORT)
        httpd = server_class(server_address, handler_class)
        thread = threading.Thread(target=httpd.serve_forever)
        thread.daemon = True
        thread.start()
        # yield thread.start()
        # Teardown code can be placed here
    except Exception as ex:
        print(ex)
        raise

    return
