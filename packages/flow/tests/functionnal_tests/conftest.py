import pytest

import tests.functionnal_tests as functionnal_tests


@pytest.fixture(autouse=True)
def _mock_local_user_configuration():
    with functionnal_tests.mocked_local_user_configuration():
        yield
