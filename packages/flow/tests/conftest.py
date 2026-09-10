# in conftest.py to load the .env file before any test is run or any import is done

import contextlib
import dotenv
import os

dotenv.load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

import mock
import pytest

import octobot.community.node_journal.constants as journal_constants


@contextlib.contextmanager
def disabled_node_journal_environment():
    with mock.patch.dict(os.environ, {journal_constants.JOURNAL_ENABLED_ENV_VAR: "false"}):
        yield


@pytest.fixture(autouse=True)
def disable_node_journal():
    with disabled_node_journal_environment():
        yield


@pytest.fixture(autouse=True)
def _disable_auto_open_in_web_browser():
    import tentacles.Meta.DSL_operators.octobot_process_operators.octobot_process_ops as octobot_process_ops
    with mock.patch.object(octobot_process_ops, "AUTO_OPEN_IN_WEB_BROWSER", False):
        yield
