#  Drakkar-Software OctoBot-Protocol
#  Copyright (c) 2026 Drakkar-Software, All rights reserved.

import json
import pathlib
import typing

import pytest

import octobot_protocol.models as protocol_models


LEGACY_TOP_LEVEL_RULES: dict[str, str] = {
    "strategy_grid_configuration.json": "strict_strategy_parse_fails",
}

LEGACY_AD_HOC_RULES: dict[str, str] = {}

DEFAULT_VERSIONED_STATE_RULE = "strict_parse_and_roundtrip"
DEFAULT_VERSIONED_USER_ACTION_RULE = "strict_user_action_parse_and_roundtrip"


class UnregisteredLegacyFixtureError(Exception):
    pass


def classify_legacy_fixture_path(legacy_root: pathlib.Path, legacy_path: pathlib.Path) -> str:
    relative_path = legacy_path.relative_to(legacy_root)
    path_parts = relative_path.parts
    if len(path_parts) == 1:
        top_level_filename = path_parts[0]
        registered_rule = LEGACY_TOP_LEVEL_RULES.get(top_level_filename)
        if registered_rule is None:
            raise UnregisteredLegacyFixtureError(
                f"Unregistered top-level legacy fixture: {top_level_filename}"
            )
        return registered_rule
    if path_parts[0] == "ad_hoc":
        ad_hoc_filename = path_parts[-1]
        registered_rule = LEGACY_AD_HOC_RULES.get(ad_hoc_filename)
        if registered_rule is None:
            raise UnregisteredLegacyFixtureError(
                f"Unregistered legacy/ad_hoc fixture: {ad_hoc_filename}"
            )
        return registered_rule
    if path_parts[0].startswith("v"):
        if "user_actions" in path_parts:
            return DEFAULT_VERSIONED_USER_ACTION_RULE
        return DEFAULT_VERSIONED_STATE_RULE
    raise UnregisteredLegacyFixtureError(f"Unknown legacy fixture path: {relative_path}")


def _fixture_stem_to_schema_name(fixture_stem: str) -> str:
    name_parts = fixture_stem.split("_")
    return "".join(part.capitalize() for part in name_parts)


def _legacy_fixture_schema_name(legacy_path: pathlib.Path) -> str:
    if legacy_path.parent.name == "user_actions":
        return "UserAction"
    return _fixture_stem_to_schema_name(legacy_path.stem)


def apply_legacy_fixture_rule(
    rule: str,
    payload: dict[str, typing.Any],
    legacy_path: pathlib.Path,
) -> None:
    if rule == "strict_strategy_parse_fails":
        with pytest.raises(ValueError):
            protocol_models.Strategy.from_dict(payload)
        return
    if rule == "strict_user_action_parse_and_roundtrip":
        reparsed_action = protocol_models.UserAction.from_json(json.dumps(payload))
        assert reparsed_action is not None
        reparsed_again = protocol_models.UserAction.from_json(reparsed_action.to_json())
        assert reparsed_again is not None
        return
    if rule == "strict_parse_and_roundtrip":
        schema_name = _legacy_fixture_schema_name(legacy_path)
        model_class = getattr(protocol_models, schema_name)
        reparsed_model = model_class.from_json(json.dumps(payload))
        assert reparsed_model is not None
        reparsed_again = model_class.from_json(reparsed_model.to_json())
        assert reparsed_again is not None
        return
    raise ValueError(f"Unknown legacy fixture rule: {rule}")
