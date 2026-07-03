import types

import octobot_commons.tentacles_management as tentacles_management
import octobot_tentacles_manager.api.inspector as inspector_module


class _ParentTentacle:
    pass


class _BingxTentacle(_ParentTentacle):
    pass


def _fake_tentacle_module():
    fake_module = types.ModuleType("fake_tentacle_module")
    fake_module.Bingx = _BingxTentacle
    return fake_module


class TestGetTentacleClassFromModule:
    def test_resolves_tentacle_name_case_insensitively(self):
        tentacle_class = inspector_module._get_tentacle_class_from_module(
            "bingx",
            _ParentTentacle,
            _fake_tentacle_module(),
            tentacles_management.default_parents_inspection,
        )
        assert tentacle_class is _BingxTentacle

    def test_resolves_tentacle_class_name(self):
        tentacle_class = inspector_module._get_tentacle_class_from_module(
            "Bingx",
            _ParentTentacle,
            _fake_tentacle_module(),
            tentacles_management.default_parents_inspection,
        )
        assert tentacle_class is _BingxTentacle
