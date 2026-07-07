#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.

import argparse
import os

import mock

import octobot.cli as octobot_cli
import octobot.enums as octobot_enums
import octobot_services.constants as services_constants


class TestStartNode:
    def test_start_node_disables_web_without_setting_node_api_env(self, monkeypatch):
        args = argparse.Namespace(
            master=False,
            consumer_only=False,
            host=None,
            port=None,
            no_web=False,
        )
        monkeypatch.delenv(services_constants.ENV_ENABLE_NODE_API, raising=False)
        monkeypatch.delenv(services_constants.ENV_NODE_API_ADDRESS, raising=False)
        monkeypatch.delenv(services_constants.ENV_NODE_API_PORT, raising=False)
        with mock.patch.object(octobot_cli, "start_octobot", mock.Mock()) as start_octobot_mock:
            octobot_cli.start_node(args, default_config_file="default.json")
        assert args.no_web is True
        assert services_constants.ENV_ENABLE_NODE_API not in os.environ
        assert services_constants.ENV_NODE_API_ADDRESS not in os.environ
        assert services_constants.ENV_NODE_API_PORT not in os.environ
        start_octobot_mock.assert_called_once_with(args, "default.json")
        assert octobot_cli.constants.FORCED_DISTRIBUTION == octobot_enums.OctoBotDistribution.NODE.value
