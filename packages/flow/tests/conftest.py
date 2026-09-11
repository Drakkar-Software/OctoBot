# in conftest.py to load the .env file before any test is run or any import is done

import dotenv
import os
import sys

dotenv.load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

import mock
import pytest

_OCTOBOT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_TESTS_ROOT = os.path.join(_OCTOBOT_ROOT, "tests")
if _TESTS_ROOT not in sys.path:
    sys.path.insert(0, _TESTS_ROOT)

from test_utils.journal_test_support import disabled_node_journal_environment


@pytest.fixture(autouse=True)
def disable_node_journal():
    with disabled_node_journal_environment():
        yield


@pytest.fixture(autouse=True)
def _disable_auto_open_in_web_browser():
    import tentacles.Meta.DSL_operators.octobot_process_operators.octobot_process_ops as octobot_process_ops
    with mock.patch.object(octobot_process_ops, "AUTO_OPEN_IN_WEB_BROWSER", False):
        yield
