#  Drakkar-Software OctoBot-Commons
#  Copyright (c) Drakkar-Software, All rights reserved.

import pytest

import octobot_commons.constants as constants


@pytest.fixture(autouse=True)
def reset_sync_data_root_env(monkeypatch):
    monkeypatch.delenv(constants.ENV_OCTOBOT_SYNC_DATA_ROOT, raising=False)
