#  Drakkar-Software OctoBot-Protocol
#  Copyright (c) 2026 Drakkar-Software, All rights reserved.
#
# Shared library for protocol backwards-compat tooling and tests.
#
# - Schema manifest: structural summary of openapi.json (property types, required fields,
#   oneOf/discriminator shapes) stored in test/compat/static/openapi_schema_manifest.json.
# - Manifest diff: detects breaking OpenAPI edits vs non-breaking manifest refresh needs.
# - Minimal instances: build smallest valid dicts from OpenAPI for wire fixtures and roundtrips.
# - Wire paths: test/compat/static/wire/ (versioned JSON consumed by sync, node, flow tests).
#
# Used by scripts/build_openapi_schema_manifest.py, scripts/build_wire_fixtures.py, and test/compat/.

import copy
import json
import os
import pathlib
import typing


_OPENAPI_REF_PREFIX = "#/components/schemas/"


class OpenApiCompatError(Exception):
    pass


class BreakingSchemaChangeError(OpenApiCompatError):
    """Raised when openapi.json changes incompatibly with the committed manifest baseline."""


class StaleManifestError(OpenApiCompatError):
    """Raised when openapi.json changed in a non-breaking way but manifest was not regenerated."""


# --- Package layout paths (test/compat/static is never cleaned by codegen) ---

def protocol_package_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[2]


def openapi_path() -> pathlib.Path:
    return protocol_package_root() / "openapi.json"


def static_dir() -> pathlib.Path:
    return protocol_package_root() / "test" / "compat" / "static"


def manifest_baseline_path() -> pathlib.Path:
    return static_dir() / "openapi_schema_manifest.json"


def wire_root_dir() -> pathlib.Path:
    env_override = os.environ.get("PROTOCOL_STATIC_WIRE_DIR")
    if env_override:
        return pathlib.Path(env_override)
    return static_dir() / "wire"


def active_version_path() -> pathlib.Path:
    return wire_root_dir() / "active_version.json"


def load_openapi_document(openapi_file: pathlib.Path | None = None) -> dict[str, typing.Any]:
    openapi_file = openapi_file or openapi_path()
    with open(openapi_file, encoding="utf-8") as handle:
        return json.load(handle)


def resolve_ref(ref: str, schemas: dict[str, typing.Any]) -> dict[str, typing.Any]:
    if not ref.startswith(_OPENAPI_REF_PREFIX):
        raise OpenApiCompatError(f"Unsupported ref format: {ref}")
    schema_name = ref[len(_OPENAPI_REF_PREFIX):]
    if schema_name not in schemas:
        raise OpenApiCompatError(f"Missing schema for ref: {ref}")
    return schemas[schema_name]


def _type_signature(
    schema: dict[str, typing.Any],
    schemas: dict[str, typing.Any],
) -> str:
    # Compact type label for manifest entries (refs, primitives, arrays, oneOf/allOf).
    if "$ref" in schema:
        ref_name = schema["$ref"][len(_OPENAPI_REF_PREFIX):]
        return f"ref:{ref_name}"
    schema_type = schema.get("type")
    if schema_type == "string":
        if "enum" in schema:
            return "enum"
        return "string"
    if schema_type == "integer":
        return "integer"
    if schema_type == "number":
        return "number"
    if schema_type == "boolean":
        return "boolean"
    if schema_type == "array":
        items = schema.get("items", {})
        return f"array:{_type_signature(items, schemas)}"
    if schema_type == "object":
        return "object"
    if "oneOf" in schema:
        return "oneOf"
    if "allOf" in schema:
        return "allOf"
    if "enum" in schema:
        return "enum"
    return "unknown"


def _collect_one_of_variants(
    schema: dict[str, typing.Any],
    schemas: dict[str, typing.Any],
) -> typing.Optional[dict[str, list[str]]]:
    if "oneOf" not in schema:
        return None
    discriminator = schema.get("discriminator", {})
    property_name = discriminator.get("propertyName")
    mapping = discriminator.get("mapping", {})
    variant_names: list[str] = []
    for one_of_entry in schema["oneOf"]:
        if "$ref" in one_of_entry:
            variant_names.append(one_of_entry["$ref"][len(_OPENAPI_REF_PREFIX):])
    one_of_info: dict[str, typing.Any] = {"variants": sorted(variant_names)}
    if property_name:
        one_of_info["discriminator"] = property_name
        one_of_info["mapping_keys"] = sorted(mapping.keys())
    return one_of_info


def build_schema_manifest(openapi_document: dict[str, typing.Any]) -> dict[str, typing.Any]:
    """Build a structural manifest for every component schema (stdlib-only contract)."""
    schemas = openapi_document["components"]["schemas"]
    manifest: dict[str, typing.Any] = {}
    for schema_name, schema in sorted(schemas.items()):
        if "enum" in schema and schema.get("type") == "string":
            manifest[schema_name] = {
                "kind": "enum",
                "values": sorted(schema["enum"]),
            }
            continue
        if schema.get("type") != "object" and "oneOf" not in schema and "allOf" not in schema:
            if "enum" in schema:
                manifest[schema_name] = {
                    "kind": "enum",
                    "values": sorted(schema["enum"]),
                }
            continue
        properties: dict[str, str] = {}
        object_schema = schema
        if "allOf" in schema:
            merged_properties: dict[str, typing.Any] = {}
            merged_required: list[str] = []
            for part in schema["allOf"]:
                if "$ref" in part:
                    part = resolve_ref(part["$ref"], schemas)
                merged_properties.update(part.get("properties", {}))
                merged_required.extend(part.get("required", []))
            object_schema = {
                "type": "object",
                "properties": merged_properties,
                "required": sorted(set(merged_required)),
            }
        for property_name, property_schema in object_schema.get("properties", {}).items():
            properties[property_name] = _type_signature(property_schema, schemas)
        entry: dict[str, typing.Any] = {
            "kind": "object",
            "properties": properties,
            "required": sorted(object_schema.get("required", [])),
        }
        one_of_info = _collect_one_of_variants(schema, schemas)
        if one_of_info is not None:
            entry["one_of"] = one_of_info
        manifest[schema_name] = entry
    return manifest


def _enum_values_from_manifest_entry(entry: dict[str, typing.Any]) -> typing.Optional[list[str]]:
    if entry.get("kind") == "enum":
        return list(entry.get("values", []))
    return None


def _manifest_properties_breaking_messages(
    schema_name: str,
    baseline_entry: dict[str, typing.Any],
    current_entry: dict[str, typing.Any],
) -> list[str]:
    messages: list[str] = []
    baseline_properties = baseline_entry.get("properties", {})
    current_properties = current_entry.get("properties", {})
    for property_name in baseline_properties:
        if property_name not in current_properties:
            messages.append(f"{schema_name}: removed property {property_name}")
        elif baseline_properties[property_name] != current_properties[property_name]:
            messages.append(
                f"{schema_name}: type change for {property_name} "
                f"({baseline_properties[property_name]} -> {current_properties[property_name]})"
            )
    baseline_required = set(baseline_entry.get("required", []))
    current_required = set(current_entry.get("required", []))
    new_required = current_required - baseline_required
    if new_required:
        messages.append(f"{schema_name}: new required properties {sorted(new_required)}")
    return messages


def _manifest_one_of_breaking_messages(
    schema_name: str,
    baseline_entry: dict[str, typing.Any],
    current_entry: dict[str, typing.Any],
) -> list[str]:
    messages: list[str] = []
    baseline_one_of = baseline_entry.get("one_of", {})
    current_one_of = current_entry.get("one_of", {})
    removed_variants = set(baseline_one_of.get("variants", [])) - set(current_one_of.get("variants", []))
    if removed_variants:
        messages.append(f"{schema_name}: removed oneOf variants {sorted(removed_variants)}")
    removed_mapping = set(baseline_one_of.get("mapping_keys", [])) - set(current_one_of.get("mapping_keys", []))
    if removed_mapping:
        messages.append(f"{schema_name}: removed discriminator values {sorted(removed_mapping)}")
    return messages


def _manifest_schema_breaking_messages(
    schema_name: str,
    baseline_entry: dict[str, typing.Any],
    current_entry: dict[str, typing.Any],
) -> list[str]:
    baseline_enum = _enum_values_from_manifest_entry(baseline_entry)
    current_enum = _enum_values_from_manifest_entry(current_entry)
    if baseline_enum is not None and current_enum is not None:
        removed_enum_values = set(baseline_enum) - set(current_enum)
        if removed_enum_values:
            return [f"{schema_name}: removed enum values {sorted(removed_enum_values)}"]
        return []
    if baseline_entry.get("kind") != current_entry.get("kind"):
        return [f"{schema_name}: kind changed"]
    messages = _manifest_properties_breaking_messages(schema_name, baseline_entry, current_entry)
    messages.extend(_manifest_one_of_breaking_messages(schema_name, baseline_entry, current_entry))
    return messages


def _breaking_manifest_diff(
    baseline: dict[str, typing.Any],
    current: dict[str, typing.Any],
) -> list[str]:
    # Breaking = removed schemas/properties, stricter required fields, removed enum/oneOf variants.
    breaking_messages: list[str] = []
    for schema_name in baseline:
        if schema_name not in current:
            breaking_messages.append(f"Removed schema: {schema_name}")
            continue
        breaking_messages.extend(
            _manifest_schema_breaking_messages(schema_name, baseline[schema_name], current[schema_name])
        )
    return breaking_messages


def compare_manifest_to_baseline(
    current_manifest: dict[str, typing.Any],
    baseline_manifest: dict[str, typing.Any],
) -> None:
    """Fail the test if manifest differs: breaking changes error; else stale manifest error."""
    if current_manifest == baseline_manifest:
        return
    breaking_messages = _breaking_manifest_diff(baseline_manifest, current_manifest)
    if breaking_messages:
        raise BreakingSchemaChangeError(
            "Breaking OpenAPI schema changes detected:\n" + "\n".join(breaking_messages)
        )
    raise StaleManifestError(
        "openapi.json changed without updating openapi_schema_manifest.json. "
        "Run: python scripts/build_openapi_schema_manifest.py"
    )


def write_json(path: pathlib.Path, payload: typing.Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")


def read_json(path: pathlib.Path) -> typing.Any:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _default_string_value(property_schema: dict[str, typing.Any], property_name: str = "") -> str:
    # Stable placeholder strings so generated wire JSON is readable and deterministic.
    if "enum" in property_schema:
        return property_schema["enum"][0]
    if property_schema.get("format") == "date-time":
        return "2020-01-01T00:00:00Z"
    if property_name in {"id", "account_id", "strategy_id"} or property_name.endswith("_id"):
        return "id-1"
    if property_name == "version":
        return "1.0.0"
    if property_name == "name":
        return "name"
    return "x"


def _build_minimal_one_of(
    schema: dict[str, typing.Any],
    schemas: dict[str, typing.Any],
    context: dict[str, typing.Any],
) -> typing.Any:
    discriminator = schema.get("discriminator", {})
    property_name = discriminator.get("propertyName")
    mapping = discriminator.get("mapping", {})
    if property_name and mapping:
        discriminator_value = sorted(mapping.keys())[0]
        ref = mapping[discriminator_value]
        variant_schema = resolve_ref(ref, schemas)
        variant_payload = _build_minimal_value(variant_schema, schemas, context)
        if isinstance(variant_payload, dict):
            variant_payload[property_name] = discriminator_value
        return variant_payload
    first_variant = schema["oneOf"][0]
    return _build_minimal_value(first_variant, schemas, context)


def _build_minimal_all_of(
    schema: dict[str, typing.Any],
    schemas: dict[str, typing.Any],
    context: dict[str, typing.Any],
) -> typing.Any:
    merged: dict[str, typing.Any] = {}
    for part in schema["allOf"]:
        part_value = _build_minimal_value(part, schemas, context)
        if isinstance(part_value, dict):
            merged.update(part_value)
    return merged


def _build_minimal_array(
    schema: dict[str, typing.Any],
    schemas: dict[str, typing.Any],
    context: dict[str, typing.Any],
) -> typing.Any:
    item_schema = schema.get("items", {})
    if context.get("prefer_nonempty_array"):
        return [_build_minimal_value(item_schema, schemas, context)]
    if item_schema.get("$ref") or item_schema.get("type") == "object" or "oneOf" in item_schema:
        return []
    return [_build_minimal_value(item_schema, schemas, context)]


def _build_minimal_object(
    schema: dict[str, typing.Any],
    schemas: dict[str, typing.Any],
    context: dict[str, typing.Any],
) -> typing.Any:
    payload: dict[str, typing.Any] = {}
    properties = schema.get("properties", {})
    required_fields = schema.get("required", [])
    for field_name in required_fields:
        if field_name in properties:
            payload[field_name] = _build_minimal_value(
                properties[field_name],
                schemas,
                {**context, "property_name": field_name},
            )
    return payload


def _build_minimal_value(
    schema: dict[str, typing.Any],
    schemas: dict[str, typing.Any],
    context: dict[str, typing.Any],
) -> typing.Any:
    # Recursively fill required fields only; optional fields omitted unless prefer_nonempty_array.
    if "$ref" in schema:
        resolved = resolve_ref(schema["$ref"], schemas)
        ref_name = schema["$ref"][len(_OPENAPI_REF_PREFIX):]
        return _build_minimal_value(resolved, schemas, {**context, "schema_name": ref_name})
    if "oneOf" in schema:
        return _build_minimal_one_of(schema, schemas, context)
    if "allOf" in schema:
        return _build_minimal_all_of(schema, schemas, context)
    schema_type = schema.get("type")
    if schema_type == "string":
        return _default_string_value(schema, context.get("property_name", ""))
    if schema_type == "integer":
        return 1
    if schema_type == "number":
        return 1.0
    if schema_type == "boolean":
        return False
    if schema_type == "array":
        return _build_minimal_array(schema, schemas, context)
    if schema_type == "object":
        return _build_minimal_object(schema, schemas, context)
    if "enum" in schema:
        return schema["enum"][0]
    return None


def build_minimal_instance(schema_name: str, openapi_document: dict[str, typing.Any]) -> typing.Any:
    schemas = openapi_document["components"]["schemas"]
    if schema_name not in schemas:
        raise OpenApiCompatError(f"Unknown schema: {schema_name}")
    schema = schemas[schema_name]
    return _build_minimal_value(schema, schemas, {"schema_name": schema_name})


def build_minimal_roundtrip_instance(schema_name: str, openapi_document: dict[str, typing.Any]) -> typing.Any:
    # prefer_nonempty_array forces at least one array element for roundtrip coverage.
    schemas = openapi_document["components"]["schemas"]
    if schema_name not in schemas:
        raise OpenApiCompatError(f"Unknown schema: {schema_name}")
    schema = schemas[schema_name]
    return _build_minimal_value(
        schema,
        schemas,
        {"schema_name": schema_name, "prefer_nonempty_array": True},
    )


# Schemas and discriminators that must have committed wire JSON under the active version.
STATE_ENVELOPE_SCHEMA_NAMES = [
    "StrategiesState",
    "AccountsState",
    "UserActionsState",
    "UserDataState",
    "DebugState",
    "DslKeywordsState",
    "PortfolioHistoricalValuesState",
    "AccountTradingState",
    "AccountsAuthenticationState",
]

USER_ACTION_CONFIGURATION_DISCRIMINATORS = [
    "automation_create",
    "automation_edit",
    "automation_stop",
    "automation_restart",
    "automation_signal",
    "account_create",
    "account_edit",
    "account_delete",
    "update_historical_exchanges_data",
    "reset_account_trading_data",
    "exchange_config_create",
    "exchange_config_edit",
    "exchange_config_delete",
    "accounts_refresh",
    "strategy_create",
    "strategy_edit",
    "strategy_delete",
    "account_auth_create",
    "account_auth_edit",
    "account_auth_delete",
]


def read_active_wire_version(wire_dir: pathlib.Path | None = None) -> str:
    wire_dir = wire_dir or wire_root_dir()
    active_version_file = wire_dir / "active_version.json"
    payload = read_json(active_version_file)
    version = payload.get("version")
    if not version:
        raise OpenApiCompatError("active_version.json is missing version")
    return str(version)


def active_wire_version_dir(wire_dir: pathlib.Path | None = None) -> pathlib.Path:
    wire_dir = wire_dir or wire_root_dir()
    version = read_active_wire_version(wire_dir)
    return wire_dir / f"v{version}"


def deep_merge_dict(
    base: dict[str, typing.Any],
    override: dict[str, typing.Any],
) -> dict[str, typing.Any]:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge_dict(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged

