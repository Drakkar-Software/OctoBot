#  Drakkar-Software OctoBot-Protocol
#  Copyright (c) 2026 Drakkar-Software, All rights reserved.
#
# Unit tests for openapi_compat_lib manifest diff classification (breaking vs stale).

import pytest

import scripts.lib.openapi_compat_lib as openapi_compat_lib


def _object_manifest(
    schema_name: str,
    properties: dict[str, str],
    required: tuple[str, ...] = (),
    one_of: dict | None = None,
) -> dict:
    entry: dict = {
        "kind": "object",
        "properties": properties,
        "required": sorted(required),
    }
    if one_of is not None:
        entry["one_of"] = one_of
    return {schema_name: entry}


def _enum_manifest(schema_name: str, values: list[str]) -> dict:
    return {schema_name: {"kind": "enum", "values": sorted(values)}}


def _minimal_openapi(schemas: dict) -> dict:
    return {
        "openapi": "3.0.0",
        "info": {"title": "test", "version": "1.0.0"},
        "paths": {},
        "components": {"schemas": schemas},
    }


class TestCompareManifestToBaseline:
    def test_identical_manifests_pass(self):
        baseline = _object_manifest("Foo", {"a": "string"}, ("a",))
        openapi_compat_lib.compare_manifest_to_baseline(baseline, baseline)

    def test_removed_schema_is_breaking(self):
        baseline = _object_manifest("Foo", {"a": "string"}, ("a",))
        current: dict = {}
        with pytest.raises(openapi_compat_lib.BreakingSchemaChangeError) as raised:
            openapi_compat_lib.compare_manifest_to_baseline(current, baseline)
        assert "Removed schema: Foo" in str(raised.value)

    def test_removed_enum_value_is_breaking(self):
        baseline = _enum_manifest("Color", ["red", "blue"])
        current = _enum_manifest("Color", ["red"])
        with pytest.raises(openapi_compat_lib.BreakingSchemaChangeError) as raised:
            openapi_compat_lib.compare_manifest_to_baseline(current, baseline)
        assert "removed enum values" in str(raised.value)
        assert "blue" in str(raised.value)

    def test_kind_change_is_breaking(self):
        baseline = _object_manifest("Foo", {"a": "string"})
        current = _enum_manifest("Foo", ["x"])
        with pytest.raises(openapi_compat_lib.BreakingSchemaChangeError) as raised:
            openapi_compat_lib.compare_manifest_to_baseline(current, baseline)
        assert "Foo: kind changed" in str(raised.value)

    def test_removed_property_is_breaking(self):
        baseline = _object_manifest("Foo", {"a": "string", "b": "integer"}, ("a",))
        current = _object_manifest("Foo", {"a": "string"}, ("a",))
        with pytest.raises(openapi_compat_lib.BreakingSchemaChangeError) as raised:
            openapi_compat_lib.compare_manifest_to_baseline(current, baseline)
        assert "removed property b" in str(raised.value)

    def test_property_type_change_is_breaking(self):
        baseline = _object_manifest("Foo", {"a": "string"}, ("a",))
        current = _object_manifest("Foo", {"a": "integer"}, ("a",))
        with pytest.raises(openapi_compat_lib.BreakingSchemaChangeError) as raised:
            openapi_compat_lib.compare_manifest_to_baseline(current, baseline)
        assert "type change for a" in str(raised.value)

    def test_new_required_property_is_breaking(self):
        baseline = _object_manifest("Foo", {"a": "string", "b": "string"}, ("a",))
        current = _object_manifest("Foo", {"a": "string", "b": "string"}, ("a", "b"))
        with pytest.raises(openapi_compat_lib.BreakingSchemaChangeError) as raised:
            openapi_compat_lib.compare_manifest_to_baseline(current, baseline)
        assert "new required properties" in str(raised.value)
        assert "b" in str(raised.value)

    def test_removed_one_of_variant_is_breaking(self):
        one_of = {"variants": ["VariantA", "VariantB"], "discriminator": "type", "mapping_keys": ["a", "b"]}
        baseline = _object_manifest("Foo", {"type": "string"}, one_of=one_of)
        current_one_of = {
            "variants": ["VariantA"],
            "discriminator": "type",
            "mapping_keys": ["a", "b"],
        }
        current = _object_manifest("Foo", {"type": "string"}, one_of=current_one_of)
        with pytest.raises(openapi_compat_lib.BreakingSchemaChangeError) as raised:
            openapi_compat_lib.compare_manifest_to_baseline(current, baseline)
        assert "removed oneOf variants" in str(raised.value)
        assert "VariantB" in str(raised.value)

    def test_removed_discriminator_mapping_key_is_breaking(self):
        one_of = {"variants": ["VariantA"], "discriminator": "type", "mapping_keys": ["a", "b"]}
        baseline = _object_manifest("Foo", {"type": "string"}, one_of=one_of)
        current_one_of = {
            "variants": ["VariantA"],
            "discriminator": "type",
            "mapping_keys": ["a"],
        }
        current = _object_manifest("Foo", {"type": "string"}, one_of=current_one_of)
        with pytest.raises(openapi_compat_lib.BreakingSchemaChangeError) as raised:
            openapi_compat_lib.compare_manifest_to_baseline(current, baseline)
        assert "removed discriminator values" in str(raised.value)
        assert "b" in str(raised.value)

    def test_multiple_breaking_changes_reported_together(self):
        baseline = {
            **_object_manifest("Foo", {"a": "string", "b": "string"}, ("a",)),
            **_enum_manifest("Color", ["red", "blue"]),
        }
        current = _object_manifest("Foo", {"a": "integer"}, ("a", "b"))
        with pytest.raises(openapi_compat_lib.BreakingSchemaChangeError) as raised:
            openapi_compat_lib.compare_manifest_to_baseline(current, baseline)
        error_text = str(raised.value)
        assert "type change for a" in error_text
        assert "new required properties" in error_text
        assert "Removed schema: Color" in error_text

    def test_added_schema_is_stale_not_breaking(self):
        baseline = _object_manifest("Foo", {"a": "string"}, ("a",))
        current = {
            **baseline,
            **_object_manifest("Bar", {"x": "string"}, ("x",)),
        }
        with pytest.raises(openapi_compat_lib.StaleManifestError):
            openapi_compat_lib.compare_manifest_to_baseline(current, baseline)

    def test_added_optional_property_is_stale(self):
        baseline = _object_manifest("Foo", {"a": "string"}, ("a",))
        current = _object_manifest("Foo", {"a": "string", "b": "integer"}, ("a",))
        with pytest.raises(openapi_compat_lib.StaleManifestError):
            openapi_compat_lib.compare_manifest_to_baseline(current, baseline)

    def test_added_enum_value_is_stale(self):
        baseline = _enum_manifest("Color", ["red"])
        current = _enum_manifest("Color", ["red", "blue"])
        with pytest.raises(openapi_compat_lib.StaleManifestError):
            openapi_compat_lib.compare_manifest_to_baseline(current, baseline)

    def test_relaxed_required_is_stale(self):
        baseline = _object_manifest("Foo", {"a": "string", "b": "string"}, ("a", "b"))
        current = _object_manifest("Foo", {"a": "string", "b": "string"}, ("a",))
        with pytest.raises(openapi_compat_lib.StaleManifestError):
            openapi_compat_lib.compare_manifest_to_baseline(current, baseline)

    def test_added_one_of_variant_is_stale(self):
        one_of = {"variants": ["VariantA"], "discriminator": "type", "mapping_keys": ["a"]}
        baseline = _object_manifest("Foo", {"type": "string"}, one_of=one_of)
        current_one_of = {
            "variants": ["VariantA", "VariantB"],
            "discriminator": "type",
            "mapping_keys": ["a"],
        }
        current = _object_manifest("Foo", {"type": "string"}, one_of=current_one_of)
        with pytest.raises(openapi_compat_lib.StaleManifestError):
            openapi_compat_lib.compare_manifest_to_baseline(current, baseline)

    def test_added_discriminator_mapping_key_is_stale(self):
        one_of = {"variants": ["VariantA"], "discriminator": "type", "mapping_keys": ["a"]}
        baseline = _object_manifest("Foo", {"type": "string"}, one_of=one_of)
        current_one_of = {
            "variants": ["VariantA"],
            "discriminator": "type",
            "mapping_keys": ["a", "b"],
        }
        current = _object_manifest("Foo", {"type": "string"}, one_of=current_one_of)
        with pytest.raises(openapi_compat_lib.StaleManifestError):
            openapi_compat_lib.compare_manifest_to_baseline(current, baseline)


class TestBuildSchemaManifestBreakingPipeline:
    def test_new_required_field_from_openapi_is_breaking(self):
        baseline_openapi = _minimal_openapi(
            {
                "Foo": {
                    "type": "object",
                    "properties": {"a": {"type": "string"}, "b": {"type": "string"}},
                    "required": ["a"],
                }
            }
        )
        current_openapi = _minimal_openapi(
            {
                "Foo": {
                    "type": "object",
                    "properties": {"a": {"type": "string"}, "b": {"type": "string"}},
                    "required": ["a", "b"],
                }
            }
        )
        baseline_manifest = openapi_compat_lib.build_schema_manifest(baseline_openapi)
        current_manifest = openapi_compat_lib.build_schema_manifest(current_openapi)
        with pytest.raises(openapi_compat_lib.BreakingSchemaChangeError) as raised:
            openapi_compat_lib.compare_manifest_to_baseline(current_manifest, baseline_manifest)
        assert "new required properties" in str(raised.value)

    def test_removed_enum_value_from_openapi_is_breaking(self):
        baseline_openapi = _minimal_openapi(
            {
                "Color": {
                    "type": "string",
                    "enum": ["red", "blue"],
                }
            }
        )
        current_openapi = _minimal_openapi(
            {
                "Color": {
                    "type": "string",
                    "enum": ["red"],
                }
            }
        )
        baseline_manifest = openapi_compat_lib.build_schema_manifest(baseline_openapi)
        current_manifest = openapi_compat_lib.build_schema_manifest(current_openapi)
        with pytest.raises(openapi_compat_lib.BreakingSchemaChangeError) as raised:
            openapi_compat_lib.compare_manifest_to_baseline(current_manifest, baseline_manifest)
        assert "removed enum values" in str(raised.value)

    def test_added_enum_value_from_openapi_is_stale(self):
        baseline_openapi = _minimal_openapi(
            {
                "Color": {
                    "type": "string",
                    "enum": ["red"],
                }
            }
        )
        current_openapi = _minimal_openapi(
            {
                "Color": {
                    "type": "string",
                    "enum": ["red", "blue"],
                }
            }
        )
        baseline_manifest = openapi_compat_lib.build_schema_manifest(baseline_openapi)
        current_manifest = openapi_compat_lib.build_schema_manifest(current_openapi)
        with pytest.raises(openapi_compat_lib.StaleManifestError):
            openapi_compat_lib.compare_manifest_to_baseline(current_manifest, baseline_manifest)

    def test_removed_one_of_variant_from_openapi_is_breaking(self):
        baseline_openapi = _minimal_openapi(
            {
                "VariantA": {
                    "type": "object",
                    "properties": {"type": {"type": "string", "enum": ["a"]}},
                    "required": ["type"],
                },
                "VariantB": {
                    "type": "object",
                    "properties": {"type": {"type": "string", "enum": ["b"]}},
                    "required": ["type"],
                },
                "Foo": {
                    "oneOf": [
                        {"$ref": "#/components/schemas/VariantA"},
                        {"$ref": "#/components/schemas/VariantB"},
                    ],
                    "discriminator": {
                        "propertyName": "type",
                        "mapping": {
                            "a": "#/components/schemas/VariantA",
                            "b": "#/components/schemas/VariantB",
                        },
                    },
                },
            }
        )
        current_openapi = _minimal_openapi(
            {
                "VariantA": {
                    "type": "object",
                    "properties": {"type": {"type": "string", "enum": ["a"]}},
                    "required": ["type"],
                },
                "Foo": {
                    "oneOf": [{"$ref": "#/components/schemas/VariantA"}],
                    "discriminator": {
                        "propertyName": "type",
                        "mapping": {"a": "#/components/schemas/VariantA"},
                    },
                },
            }
        )
        baseline_manifest = openapi_compat_lib.build_schema_manifest(baseline_openapi)
        current_manifest = openapi_compat_lib.build_schema_manifest(current_openapi)
        with pytest.raises(openapi_compat_lib.BreakingSchemaChangeError) as raised:
            openapi_compat_lib.compare_manifest_to_baseline(current_manifest, baseline_manifest)
        assert "removed oneOf variants" in str(raised.value)
