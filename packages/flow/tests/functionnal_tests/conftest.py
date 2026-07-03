import os
import pathlib

import pytest

import octobot_commons.constants as commons_constants

import tests.functionnal_tests as functionnal_tests


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
