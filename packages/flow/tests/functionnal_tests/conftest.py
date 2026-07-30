import os
import pathlib

import pytest

import octobot_commons.constants as commons_constants
import octobot_trading.errors as trading_errors

import octobot_flow.environment
import tests.functionnal_tests as functionnal_tests


@pytest.fixture
def skip_on_exchange_proxy_error(request):
    """Opt-in: convert ExchangeProxyError during the test call into a skip."""

    class _SkipOnExchangeProxyErrorPlugin:
        @pytest.hookimpl(hookwrapper=True)
        def pytest_runtest_makereport(self, item, call):
            outcome = yield
            report = outcome.get_result()
            if item is not request.node:
                return
            if call.when != "call" or call.excinfo is None:
                return
            if not isinstance(call.excinfo.value, trading_errors.ExchangeProxyError):
                return
            proxy_url = os.environ.get("EXCHANGE_HTTP_PROXY_AUTHENTICATED_URL")
            proxy_url_part = (
                f" (EXCHANGE_HTTP_PROXY_AUTHENTICATED_URL={proxy_url})" if proxy_url else ""
            )
            skip_reason = f"Exchange proxy unavailable{proxy_url_part}: {call.excinfo.value}"
            report.outcome = "skipped"
            # pytest expects skipped longrepr as (path, lineno, "Skipped: reason")
            line_number = item.location[1] if item.location else 0
            report.longrepr = (str(item.path), line_number, f"Skipped: {skip_reason}")

    plugin = _SkipOnExchangeProxyErrorPlugin()
    request.config.pluginmanager.register(plugin)
    yield
    request.config.pluginmanager.unregister(plugin)


@pytest.fixture(autouse=True)
def _register_functional_executor_id():
    octobot_flow.environment.register_executor_id("func-test-executor")
    yield


@pytest.fixture(autouse=True)
def _mock_local_user_configuration():
    with functionnal_tests.mocked_local_user_configuration():
        yield


@pytest.fixture(autouse=True)
def _assert_master_user_config_unchanged(request):
    if not os.path.isfile(os.path.join(os.getcwd(), "start.py")):
        yield
        return
    master_config_path = pathlib.Path(commons_constants.USER_FOLDER) / commons_constants.CONFIG_FILE
    if not master_config_path.is_file():
        yield
        return
    config_bytes_before = master_config_path.read_bytes()
    yield
    config_bytes_after = master_config_path.read_bytes()
    assert config_bytes_before == config_bytes_after, (
        f"master user config must not be modified during functional test "
        f"{request.node.nodeid!r}: {master_config_path}"
    )
