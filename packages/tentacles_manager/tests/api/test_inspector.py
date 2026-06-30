import octobot_tentacles_manager.api.inspector as inspector_module


class TestGetTentacleClassFromString:
    def test_resolves_exchange_tentacle_name_case_insensitively(self):
        bingx_class = inspector_module.get_tentacle_class_from_string("bingx", allow_cache=False)
        assert bingx_class.__name__ == "Bingx"

    def test_resolves_exchange_tentacle_class_name(self):
        bingx_class = inspector_module.get_tentacle_class_from_string("Bingx", allow_cache=False)
        assert bingx_class.__name__ == "Bingx"
