#  Drakkar-Software OctoBot-Interfaces
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import datetime
import flask
import werkzeug.http as werk_http
import urllib.parse as url_parse


CACHE_CONTROL_KEY = 'Cache-Control'


def register_responses_extra_header(flask_app, high_security_level):
    # prepare extra response headers, see after_request
    response_extra_headers = _prepare_response_extra_headers(high_security_level)

    no_cache_headers = {
        CACHE_CONTROL_KEY: 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0',
        'Last-Modified': werk_http.http_date(datetime.datetime.now()),
    }

    @flask_app.after_request
    def after_request(response):
        if CACHE_CONTROL_KEY not in response.headers:
            response.headers.extend(no_cache_headers)
        response.headers.extend(response_extra_headers)
        return response


def _prepare_response_extra_headers(include_security_headers):
    response_extra_headers = {
        # uncomment to completely disable client caching (js and css files etc)
        # 'Cache-Control': 'no-cache, no-store, must-revalidate',
        # 'Pragma': 'no-cache',
        # 'Expires': '0',
        # 'Last-Modified': werk_http.http_date(datetime.now()),
    }
    if include_security_headers:
        response_security_headers = {
            # X-Frame-Options: page can only be shown in an iframe of the same site
            'X-Frame-Options': 'SAMEORIGIN',
            # ensure all app communication is sent over HTTPS
            'Strict-Transport-Security': 'max-age=63072000; includeSubdomains',
            # instructs the browser not to override the response content type
            'X-Content-Type-Options': 'nosniff',
            # enable browser cross-site scripting (XSS) filter
            'X-XSS-Protection': '1; mode=block',
        }
        response_extra_headers.update(response_security_headers)

    return response_extra_headers


def is_safe_url(target):
    ref_url = url_parse.urlparse(flask.request.host_url)
    test_url = url_parse.urlparse(url_parse.urljoin(flask.request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
        ref_url.netloc == test_url.netloc
