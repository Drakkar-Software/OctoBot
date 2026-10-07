#  Drakkar-Software OctoBot-Tentacles
#  Copyright (c) Drakkar-Software, All rights reserved.

import json

import tentacles.Services.Interfaces.web_interface.websockets.protocol.wire_protocol as wire_protocol


class TestEncodeWsEvent:
    def test_round_trip_with_data(self):
        encoded = wire_protocol.encode_ws_event("profitability", {"value": 1})
        event, data = wire_protocol.decode_ws_event(encoded)
        assert event == "profitability"
        assert data == {"value": 1}

    def test_round_trip_without_data(self):
        encoded = wire_protocol.encode_ws_event("backtesting_status")
        event, data = wire_protocol.decode_ws_event(encoded)
        assert event == "backtesting_status"
        assert data is None


class TestBuildWsClientUrl:
    def test_ws_scheme_and_namespace(self):
        url = wire_protocol.build_ws_client_url("localhost:5001", "/dashboard", secure=False)
        assert url == "ws://localhost:5001/dashboard"

    def test_wss_scheme(self):
        url = wire_protocol.build_ws_client_url("localhost", "/notifications", secure=True)
        assert url == "wss://localhost/notifications"

    def test_base_path_prefix(self):
        url = wire_protocol.build_ws_client_url(
            "localhost",
            "/dashboard",
            secure=False,
            base_path="/octobot",
        )
        assert url == "ws://localhost/octobot/dashboard"
