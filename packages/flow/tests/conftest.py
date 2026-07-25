# in conftest.py to load the .env file before any test is run or any import is done

import dotenv
import os
dotenv.load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

import mock
import pytest


@pytest.fixture(autouse=True)
def _disable_auto_open_in_web_browser():
    import tentacles.Meta.DSL_operators.octobot_process_operators.octobot_process_ops as octobot_process_ops
    with mock.patch.object(octobot_process_ops, "AUTO_OPEN_IN_WEB_BROWSER", False):
        yield
