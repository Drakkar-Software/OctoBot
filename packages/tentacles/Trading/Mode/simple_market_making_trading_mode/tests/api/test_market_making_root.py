#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.

from tentacles.Trading.Mode.simple_market_making_trading_mode.tests.api.conftest import get_all_routes


def test_market_making_ping(client):
    response = client.get("/api/v1/tentacles/market-making/ping")
    assert response.status_code == 200
    assert response.content == b""


def test_all_routes_options_request(client):
    # CORSMiddleware only short-circuits as a CORS *preflight* when both Origin and
    # Access-Control-Request-Method are set; otherwise OPTIONS hits the route and can 405.
    preflight_headers = {
        "Origin": "http://testserver",
        "Access-Control-Request-Method": "GET",
    }
    for route in get_all_routes(client.app):
        response = client.options(route, headers=preflight_headers)
        assert response.status_code == 200
        headers = {header_key.lower(): header_value for header_key, header_value in response.headers.items()}
        # With allow_credentials=True, browsers require a concrete origin, not "*", so Starlette
        # echoes Access-Control-Allow-Origin: <request Origin>. With credentials off, it can be "*".
        allow_origin = headers.get("access-control-allow-origin")
        assert allow_origin in ("*", preflight_headers["Origin"]), (
            f"Failed CORS for route {route}: Access-Control-Allow-Origin is {allow_origin!r}"
        )
