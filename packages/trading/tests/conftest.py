import pytest
import mock
import octobot_tentacles_manager.constants as constants


@pytest.fixture(autouse=True)
def allow_unsigned_test_tentacles(request):
    if "signature_verification" in request.keywords:
        yield
    else:
        with mock.patch.object(constants, "ALLOW_UNSIGNED_TENTACLES", True):
            yield
