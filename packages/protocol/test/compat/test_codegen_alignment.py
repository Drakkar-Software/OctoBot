#  Drakkar-Software OctoBot-Protocol
#  Copyright (c) 2026 Drakkar-Software, All rights reserved.

import octobot_protocol.models as protocol_models
import scripts.lib.openapi_compat_lib as openapi_compat_lib

def _openapi_schema_names() -> set[str]:
    openapi_document = openapi_compat_lib.load_openapi_document()
    return set(openapi_document["components"]["schemas"].keys())


def _generated_model_names() -> set[str]:
    return {
        name
        for name in dir(protocol_models)
        if not name.startswith("_") and name[0].isupper()
    }

_ONE_OF_WRAPPER_MODELS = {
    "AccountSpecifics",
    "DslParameterDefaultValue",
    "SignalAutomationConfigurationSignalPayload",
    "StrategyConfiguration",
    "UserActionResult",
}


class TestCodegenAlignment:
    def test_openapi_schemas_match_generated_models(self):
        openapi_names = _openapi_schema_names()
        model_names = _generated_model_names()
        missing_models = sorted(openapi_names - model_names)
        extra_models = sorted(model_names - openapi_names - _ONE_OF_WRAPPER_MODELS)
        assert missing_models == [], f"OpenAPI schemas without generated models: {missing_models}"
        assert extra_models == [], f"Unexpected generated models without OpenAPI schemas: {extra_models}"

    def test_models_init_exports_match_generated_files(self):
        exported_names = {
            name
            for name in dir(protocol_models)
            if not name.startswith("_") and name[0].isupper()
        }
        models_dir = openapi_compat_lib.protocol_package_root() / "octobot_protocol" / "models"
        file_stems = {
            model_path.stem
            for model_path in models_dir.glob("*.py")
            if model_path.name != "__init__.py"
        }
        missing_files = sorted(
            name
            for name in exported_names
            if _model_name_to_module_stem(name) not in file_stems
        )
        assert missing_files == [], f"Exported models without module files: {missing_files}"


def _model_name_to_module_stem(model_name: str) -> str:
    snake_name = []
    for index, character in enumerate(model_name):
        if character.isupper() and index > 0:
            snake_name.append("_")
        snake_name.append(character.lower())
    return "".join(snake_name)
