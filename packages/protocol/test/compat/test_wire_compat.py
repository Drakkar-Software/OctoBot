#  Drakkar-Software OctoBot-Protocol
#  Copyright (c) 2026 Drakkar-Software, All rights reserved.
#
# Wire-format backwards-compat tests: committed JSON under test/compat/static/wire/
# must stay aligned with openapi.json and parse through generated models.
# Consumer packages (sync, node, flow) read the same static tree for integration tests.

import json
import os
import pathlib
import subprocess
import sys

import test.compat.legacy_fixture_expectations as legacy_fixture_expectations
import scripts.lib.openapi_compat_lib as openapi_compat_lib

import octobot_protocol.models as protocol_models


class TestWireFixtureGeneratorCheck:
    def test_wire_fixtures_are_up_to_date(self):
        # Run the fixture script as a subprocess (same as npm run check:fixtures) so this
        # test exercises the CLI entry point, cwd, and imports — not only the compare logic.
        # Pass PYTHONPATH explicitly: the child needs octobot_protocol on the import path.
        protocol_root = openapi_compat_lib.protocol_package_root()
        subprocess_env = os.environ.copy()
        if os.environ.get("PYTHONPATH"):
            subprocess_env["PYTHONPATH"] = os.environ["PYTHONPATH"]
        else:
            subprocess_env["PYTHONPATH"] = str(protocol_root)
        result = subprocess.run(
            [sys.executable, "-m", "scripts.build_wire_fixtures", "--check"],
            cwd=protocol_root,
            capture_output=True,
            text=True,
            env=subprocess_env,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr


class TestStrictWireCompat:
    def test_active_wire_fixtures_parse_and_roundtrip(self):
        # Every committed fixture for the active wire version must strict-parse and roundtrip.
        version_dir = openapi_compat_lib.active_wire_version_dir()
        fixture_paths = sorted(version_dir.rglob("*.json"))
        assert fixture_paths, "Expected active wire fixtures"
        for fixture_path in fixture_paths:
            fixture_payload = openapi_compat_lib.read_json(fixture_path)
            if fixture_path.parent.name == "user_actions":
                reparsed = protocol_models.UserAction.from_json(json.dumps(fixture_payload))
                assert reparsed is not None
                reparsed_again = protocol_models.UserAction.from_json(reparsed.to_json())
                assert reparsed_again is not None
                continue
            schema_name = _fixture_path_to_schema_name(fixture_path, version_dir)
            model_class = getattr(protocol_models, schema_name)
            reparsed = model_class.from_json(json.dumps(fixture_payload))
            assert reparsed is not None
            reparsed_again = model_class.from_json(reparsed.to_json())
            assert reparsed_again is not None


class TestFixtureCatalog:
    def test_state_envelope_fixtures_exist(self):
        # One JSON file per state envelope schema in the active wire version directory.
        version_dir = openapi_compat_lib.active_wire_version_dir()
        for schema_name in openapi_compat_lib.STATE_ENVELOPE_SCHEMA_NAMES:
            fixture_name = _schema_name_to_fixture_filename(schema_name)
            fixture_path = version_dir / fixture_name
            assert fixture_path.exists(), f"Missing fixture for {schema_name}"

    def test_user_action_configuration_fixtures_match_openapi(self):
        openapi_document = openapi_compat_lib.load_openapi_document()
        mapping = openapi_document["components"]["schemas"]["UserActionConfiguration"]["discriminator"]["mapping"]
        user_actions_dir = openapi_compat_lib.active_wire_version_dir() / "user_actions"
        fixture_names = {path.stem for path in user_actions_dir.glob("*.json")}
        assert fixture_names == set(mapping.keys())

    def test_legacy_fixtures_still_parse_or_tolerate(self):
        # legacy/ holds ad-hoc files and archived v* trees; each path has an explicit rule
        # in legacy_fixture_expectations (unregistered ad_hoc files fail this test).
        legacy_root = openapi_compat_lib.wire_root_dir() / "legacy"
        legacy_paths = sorted(legacy_root.rglob("*.json"))
        assert legacy_paths, "Expected legacy wire fixtures"
        for legacy_path in legacy_paths:
            payload = openapi_compat_lib.read_json(legacy_path)
            fixture_rule = legacy_fixture_expectations.classify_legacy_fixture_path(
                legacy_root,
                legacy_path,
            )
            legacy_fixture_expectations.apply_legacy_fixture_rule(
                fixture_rule,
                payload,
                legacy_path,
            )


def _schema_name_to_fixture_filename(schema_name: str) -> str:
    snake_name = []
    for index, character in enumerate(schema_name):
        if character.isupper() and index > 0:
            snake_name.append("_")
        snake_name.append(character.lower())
    return "".join(snake_name) + ".json"


def _fixture_path_to_schema_name(fixture_path: pathlib.Path, version_dir: pathlib.Path) -> str:
    relative_path = fixture_path.relative_to(version_dir)
    if relative_path.parent.name == "user_actions":
        return "UserAction"
    stem = relative_path.stem
    parts = stem.split("_")
    return "".join(part.capitalize() for part in parts)
