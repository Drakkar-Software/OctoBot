#  Drakkar-Software OctoBot-Protocol
#  Copyright (c) 2026 Drakkar-Software, All rights reserved.

import json

import pytest

import octobot_protocol.models as protocol_models
import scripts.lib.openapi_compat_lib as openapi_compat_lib


class TestModelRoundtrip:
    @pytest.fixture(scope="class")
    @classmethod
    def openapi_schema_names(cls):
        openapi_document = openapi_compat_lib.load_openapi_document()
        return sorted(openapi_document["components"]["schemas"].keys())

    def test_each_openapi_schema_roundtrips_through_generated_model(self, openapi_schema_names):
        openapi_document = openapi_compat_lib.load_openapi_document()
        manifest = openapi_compat_lib.build_schema_manifest(openapi_document)
        failures: list[str] = []
        for schema_name in openapi_schema_names:
            manifest_entry = manifest.get(schema_name, {})
            if manifest_entry.get("kind") == "enum":
                continue
            model_class = getattr(protocol_models, schema_name, None)
            if model_class is None:
                failures.append(f"{schema_name}: missing model class")
                continue
            if not hasattr(model_class, "from_dict"):
                continue
            try:
                minimal_dict = openapi_compat_lib.build_minimal_roundtrip_instance(
                    schema_name,
                    openapi_document,
                )
                model_instance = model_class.from_dict(minimal_dict)
                if model_instance is None:
                    failures.append(f"{schema_name}: from_dict returned None")
                    continue
                roundtrip_instance = model_class.from_json(model_instance.to_json())
                if roundtrip_instance is None:
                    failures.append(f"{schema_name}: roundtrip from_json returned None")
            except Exception as error:
                failures.append(f"{schema_name}: {error}")
        assert not failures, "Model roundtrip failures:\n" + "\n".join(failures)
