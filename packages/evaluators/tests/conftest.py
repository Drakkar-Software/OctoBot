import pytest
import mock
import octobot_tentacles_manager.constants as constants
import octobot_commons.tentacles_management as tentacles_management

import octobot_evaluators.api as evaluator_api
import octobot_evaluators.matrix.matrices as matrices

_ORIGINAL_GET_ALL_CLASSES_FROM_PARENT = tentacles_management.get_all_classes_from_parent


def _get_all_classes_from_parent_excluding_test_fakes(parent_class):
    return [
        evaluator_class
        for evaluator_class in _ORIGINAL_GET_ALL_CLASSES_FROM_PARENT(parent_class)
        if not getattr(evaluator_class, "IS_TEST_FAKE_EVALUATOR", False)
    ]


@pytest.fixture
def matrix_id():
    created_matrix_id = evaluator_api.create_matrix()
    yield created_matrix_id
    matrices.Matrices.instance().del_matrix(created_matrix_id)


@pytest.fixture(autouse=True)
def exclude_test_fake_evaluators_from_factory_discovery():
    with mock.patch.object(
        tentacles_management,
        "get_all_classes_from_parent",
        _get_all_classes_from_parent_excluding_test_fakes,
    ):
        yield


@pytest.fixture(autouse=True)
def allow_unsigned_test_tentacles(request):
    if "signature_verification" in request.keywords:
        yield
    else:
        with mock.patch.object(constants, "ALLOW_UNSIGNED_TENTACLES", True):
            yield
