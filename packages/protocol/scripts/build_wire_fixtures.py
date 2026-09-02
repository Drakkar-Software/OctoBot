#  Drakkar-Software OctoBot-Protocol
#  Copyright (c) 2026 Drakkar-Software, All rights reserved.
#
# CLI: build, check, or archive versioned wire JSON under test/compat/static/wire/.
#
# Modes (npm shortcuts in package.json):
#   --write            Regenerate active version fixtures (npm run generate:fixtures)
#   --check            Fail if committed JSON differs from model roundtrip output (npm run check:fixtures)
#   --promote-version  Archive active v* tree to legacy/v{old}/, bump active_version.json, regenerate
#   --promote-files    Copy specific active fixtures to legacy/ad_hoc/ for tolerant-load tests
#
# Fixtures are model.to_json() output (not raw OpenAPI minimal dicts) so wire bytes match
# what Python consumers actually serialize. WIRE_FIXTURE_OVERRIDES enrich empty envelopes
# (e.g. strategies_state with a real trading tentacle config).

import argparse
import copy
import json
import pathlib
import shutil
import sys
import typing

import scripts.lib.openapi_compat_lib as openapi_compat_lib


def _import_protocol_models():
    # Requires packages/protocol on PYTHONPATH (same as npm run generate:python).
    import octobot_protocol.models as protocol_models

    return protocol_models


# Richer state envelopes than OpenAPI minimal instances alone (used by sync/node consumer tests).
WIRE_FIXTURE_OVERRIDES: dict[str, dict[str, typing.Any]] = {
    "strategies_state.json": {
        "version": "1.0.0",
        "strategies": [
            {
                "id": "strat-valid",
                "version": "1",
                "reference_market": "USDC",
                "configuration": {
                    "configuration_type": "trading_tentacles",
                    "name": "DCATradingMode",
                    "config": {"trading_pairs": ["BTC/USDC"]},
                },
            }
        ],
    },
    "accounts_state.json": {
        "version": "1.0.0",
        "accounts": [],
        "exchange_configs": [],
    },
    "user_actions_state.json": {
        "version": "1.0.0",
        "user_actions": [],
    },
    "user_data_state.json": {
        "version": "1.0.0",
        "automations": [],
        "user_actions": [],
    },
    "debug_state.json": {
        "version": "1.0.0",
        "debug": {
            "automations": [],
            "user_actions": [],
        },
    },
    "dsl_keywords_state.json": {
        "version": "1.0.0",
        "keywords": [],
    },
    "portfolio_historical_values_state.json": {
        "version": "1.0.0",
    },
    "account_trading_state.json": {
        "version": "1.0.0",
        "account_trading": {
            "updated_at": "2020-01-01T00:00:00Z",
            "orders": [],
            "trades": [],
            "positions": [],
            "transactions": [],
        },
    },
    "accounts_authentication_state.json": {
        "version": "1.0.0",
        "account_authentication": [],
    },
}


def _wire_fixture_specs(protocol_models: typing.Any, compat: typing.Any) -> dict[str, typing.Any]:
    openapi_document = compat.load_openapi_document()
    state_specs: dict[str, typing.Any] = {}
    for schema_name in compat.STATE_ENVELOPE_SCHEMA_NAMES:
        filename = _schema_name_to_fixture_filename(schema_name)
        minimal_dict = compat.build_minimal_instance(schema_name, openapi_document)
        state_specs[filename] = minimal_dict
    state_specs["automation_state.json"] = compat.build_minimal_instance(
        "AutomationState",
        openapi_document,
    )
    for filename, override in WIRE_FIXTURE_OVERRIDES.items():
        if filename in state_specs:
            state_specs[filename] = compat.deep_merge_dict(state_specs[filename], override)
    return state_specs


def _schema_name_to_fixture_filename(schema_name: str) -> str:
    snake_name = []
    for index, character in enumerate(schema_name):
        if character.isupper() and index > 0:
            snake_name.append("_")
        snake_name.append(character.lower())
    return "".join(snake_name) + ".json"


def _build_user_action_for_discriminator(
    discriminator: str,
    protocol_models: typing.Any,
    compat: typing.Any,
) -> dict[str, typing.Any]:
    openapi_document = compat.load_openapi_document()
    user_action_configuration_schema = openapi_document["components"]["schemas"]["UserActionConfiguration"]
    mapping = user_action_configuration_schema["discriminator"]["mapping"]
    configuration_ref = mapping[discriminator]
    configuration_schema_name = configuration_ref[len("#/components/schemas/"):]
    configuration_dict = compat.build_minimal_instance(configuration_schema_name, openapi_document)
    configuration_dict["action_type"] = discriminator
    user_action_dict = compat.build_minimal_instance("UserAction", openapi_document)
    user_action_dict["configuration"] = configuration_dict
    user_action_dict["id"] = f"user-action-{discriminator}"
    return user_action_dict


def _normalize_json_text(payload: typing.Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _write_fixture_file(path: pathlib.Path, payload: typing.Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(_normalize_json_text(payload))


def _read_fixture_file(path: pathlib.Path) -> typing.Any:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def _collect_generated_fixtures(
    version_dir: pathlib.Path,
    protocol_models: typing.Any,
    compat: typing.Any,
) -> dict[str, typing.Any]:
    generated: dict[str, typing.Any] = {}
    state_specs = _wire_fixture_specs(protocol_models, compat)
    for filename, payload in state_specs.items():
        generated[filename] = payload
    user_actions_dir = version_dir / "user_actions"
    for discriminator in compat.USER_ACTION_CONFIGURATION_DISCRIMINATORS:
        relative_path = f"user_actions/{discriminator}.json"
        generated[relative_path] = _build_user_action_for_discriminator(
            discriminator,
            protocol_models,
            compat,
        )
    return generated


def _serialize_model_fixture(model: typing.Any) -> dict[str, typing.Any]:
    return json.loads(model.to_json())


def _build_model_fixtures(protocol_models: typing.Any, compat: typing.Any) -> dict[str, typing.Any]:
    # Serialize through generated models so wire JSON matches runtime to_json() output.
    generated: dict[str, typing.Any] = {}
    for filename, override in _wire_fixture_specs(protocol_models, compat).items():
        schema_name = _fixture_filename_to_schema_name(filename)
        model_class = getattr(protocol_models, schema_name)
        model_instance = model_class.from_dict(copy.deepcopy(override))
        if model_instance is None:
            raise RuntimeError(f"Could not build model for {schema_name}")
        generated[filename] = _serialize_model_fixture(model_instance)
    user_actions: dict[str, typing.Any] = {}
    for discriminator in compat.USER_ACTION_CONFIGURATION_DISCRIMINATORS:
        user_action_dict = _build_user_action_for_discriminator(discriminator, protocol_models, compat)
        user_action = protocol_models.UserAction.from_dict(user_action_dict)
        if user_action is None:
            raise RuntimeError(f"Could not build UserAction for {discriminator}")
        user_actions[f"user_actions/{discriminator}.json"] = _serialize_model_fixture(user_action)
    automation_state = protocol_models.AutomationState.from_dict(
        compat.build_minimal_instance("AutomationState", compat.load_openapi_document())
    )
    if automation_state is None:
        raise RuntimeError("Could not build AutomationState")
    generated["automation_state.json"] = _serialize_model_fixture(automation_state)
    generated.update(user_actions)
    return generated


def _fixture_filename_to_schema_name(filename: str) -> str:
    stem = filename.replace(".json", "")
    parts = stem.split("_")
    return "".join(part.capitalize() for part in parts)


def _write_generated_fixtures(version_dir: pathlib.Path, generated: dict[str, typing.Any]) -> None:
    for relative_path, payload in generated.items():
        _write_fixture_file(version_dir / relative_path, payload)


def _check_generated_fixtures(version_dir: pathlib.Path, generated: dict[str, typing.Any]) -> list[str]:
    mismatches: list[str] = []
    for relative_path, expected_payload in sorted(generated.items()):
        fixture_path = version_dir / relative_path
        if not fixture_path.exists():
            mismatches.append(f"Missing fixture: {relative_path}")
            continue
        current_payload = _read_fixture_file(fixture_path)
        if current_payload != expected_payload:
            mismatches.append(f"Stale fixture: {relative_path}")
    return mismatches


def _promote_version(new_version: str, compat: typing.Any, protocol_models: typing.Any) -> None:
    # Breaking-change workflow: snapshot current active tree, then regenerate fresh fixtures.
    wire_dir = compat.wire_root_dir()
    current_version = compat.read_active_wire_version(wire_dir)
    current_dir = wire_dir / f"v{current_version}"
    archive_dir = wire_dir / "legacy" / f"v{current_version}"
    if archive_dir.exists():
        raise RuntimeError(f"Legacy archive already exists: {archive_dir}")
    if current_dir.exists():
        shutil.copytree(current_dir, archive_dir)
    compat.write_json(compat.active_version_path(), {"version": new_version})
    new_dir = wire_dir / f"v{new_version}"
    generated = _build_model_fixtures(protocol_models, compat)
    _write_generated_fixtures(new_dir, generated)
    print(
        f"Promoted wire fixtures: archived v{current_version} to {archive_dir}, "
        f"active version is now v{new_version} ({len(generated)} files)"
    )


def _promote_files(relative_paths: list[str], compat: typing.Any) -> None:
    wire_dir = compat.wire_root_dir()
    version_dir = compat.active_wire_version_dir(wire_dir)
    legacy_dir = wire_dir / "legacy" / "ad_hoc"
    legacy_dir.mkdir(parents=True, exist_ok=True)
    for relative_path in relative_paths:
        source_path = version_dir / relative_path
        if not source_path.exists():
            raise RuntimeError(f"Fixture not found for promote-files: {relative_path}")
        destination_path = legacy_dir / relative_path.replace("/", "__")
        shutil.copy2(source_path, destination_path)
        print(f"Archived {relative_path} to {destination_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or check protocol wire JSON fixtures.")
    parser.add_argument("--write", action="store_true", help="Write active version wire fixtures.")
    parser.add_argument("--check", action="store_true", help="Check committed fixtures are up to date.")
    parser.add_argument("--promote-version", type=str, default=None, help="Archive active version and regenerate.")
    parser.add_argument("--promote-files", nargs="+", default=None, help="Archive specific fixtures to legacy/ad_hoc.")
    args = parser.parse_args()
    if not any([args.write, args.check, args.promote_version, args.promote_files]):
        parser.error("One of --write, --check, --promote-version, or --promote-files is required")
    compat = openapi_compat_lib
    protocol_models = _import_protocol_models()
    if args.promote_files:
        _promote_files(args.promote_files, compat)
    if args.promote_version:
        _promote_version(args.promote_version, compat, protocol_models)
        return 0
    # Default active version file if missing (first-time setup).
    wire_dir = compat.wire_root_dir()
    if not compat.active_version_path().exists():
        compat.write_json(compat.active_version_path(), {"version": "1.0.0"})
    version_dir = compat.active_wire_version_dir(wire_dir)
    generated = _build_model_fixtures(protocol_models, compat)
    if args.write:
        _write_generated_fixtures(version_dir, generated)
        print(f"Wrote {len(generated)} wire fixtures to {version_dir}")
    if args.check:
        # Byte-compare committed files to freshly generated payloads (used by test/compat subprocess).
        mismatches = _check_generated_fixtures(version_dir, generated)
        if mismatches:
            print("Wire fixture check failed:")
            for mismatch in mismatches:
                print(f"  - {mismatch}")
            print("Run: python -m scripts.build_wire_fixtures --write")
            return 1
        print(f"Wire fixtures up to date ({len(generated)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
