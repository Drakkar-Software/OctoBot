#  Drakkar-Software OctoBot-Sync
#  Copyright (c) 2026 Drakkar-Software, All rights reserved.
#
# Sync tolerant-load layer for protocol wire fixtures: committed JSON under
# test/compat/static/wire/ must load via TolerantStateLoader with sync collection/state
# wiring (active version, legacy/v*, and legacy/ad_hoc snapshots).

import json
import typing

import octobot_protocol.models as protocol_models
import scripts.lib.openapi_compat_lib as openapi_compat_lib

import tests.sync.collection_backend.tolerant_state_loading_test_support as tolerant_state_loading_test_support


def _protocol_wire_state_fixture_cases() -> list[tuple[str, str, typing.Any, dict[str, typing.Any]]]:
    return [
        (
            "strategies_state.json",
            "user-strategies",
            protocol_models.StrategiesState,
            tolerant_state_loading_test_support.strategy_tolerant_loading_kwargs(),
        ),
        (
            "accounts_state.json",
            "user-accounts",
            protocol_models.AccountsState,
            {},
        ),
        (
            "user_actions_state.json",
            "user-actions",
            protocol_models.UserActionsState,
            {},
        ),
        (
            "user_data_state.json",
            "user-data",
            protocol_models.UserDataState,
            {},
        ),
        (
            "debug_state.json",
            "debug",
            protocol_models.DebugState,
            {},
        ),
        (
            "dsl_keywords_state.json",
            "dsl-keywords",
            protocol_models.DslKeywordsState,
            {},
        ),
        (
            "portfolio_historical_values_state.json",
            "user-accounts-history",
            protocol_models.PortfolioHistoricalValuesState,
            {},
        ),
        (
            "account_trading_state.json",
            "user-accounts-trading",
            protocol_models.AccountTradingState,
            {},
        ),
        (
            "accounts_authentication_state.json",
            "user-accounts-auth",
            protocol_models.AccountsAuthenticationState,
            {},
        ),
    ]


SYNC_LEGACY_AD_HOC_EXPECTATIONS: dict[str, str] = {}


class TestProtocolWireStateFixtures:
    """Tolerant-load layer: active wire state JSON must load via TolerantStateLoader
    with sync collection/state wiring (including legacy grid strategy ad hoc case).
    """

    def test_loads_protocol_wire_state_fixtures_via_tolerant_loader(self):
        version_dir = openapi_compat_lib.active_wire_version_dir()
        for fixture_name, collection, state_class, loader_kwargs in _protocol_wire_state_fixture_cases():
            fixture_path = version_dir / fixture_name
            with open(fixture_path, encoding="utf-8") as handle:
                raw_state = json.load(handle)
            loader = tolerant_state_loading_test_support.make_loader(
                collection,
                state_class,
                **loader_kwargs,
            )
            parsed_state = loader.from_dict(raw_state)
            assert parsed_state is not None

    def test_legacy_grid_strategy_dict_loads_via_tolerant_loader(self):
        wire_dir = openapi_compat_lib.wire_root_dir()
        legacy_path = wire_dir / "legacy" / "strategy_grid_configuration.json"
        with open(legacy_path, encoding="utf-8") as handle:
            legacy_strategy = json.load(handle)
        loader = tolerant_state_loading_test_support.make_loader(
            "user-strategies",
            protocol_models.StrategiesState,
            **tolerant_state_loading_test_support.strategy_tolerant_loading_kwargs(),
        )
        parsed_state = loader.from_dict(
            {
                "version": "1.0.0",
                "strategies": [legacy_strategy],
            }
        )
        assert parsed_state is not None
        assert len(parsed_state.strategies) == 1
        assert parsed_state.strategies[0].configuration.actual_instance is None


class TestProtocolLegacyWireStateFixtures:
    """Archived legacy/v* and legacy/ad_hoc wire snapshots must still tolerant-load
    after intentional breaking changes.
    """

    def test_loads_legacy_versioned_state_fixtures_via_tolerant_loader(self):
        wire_dir = openapi_compat_lib.wire_root_dir()
        legacy_root = wire_dir / "legacy"
        for version_dir in sorted(legacy_root.glob("v*")):
            for fixture_name, collection, state_class, loader_kwargs in _protocol_wire_state_fixture_cases():
                fixture_path = version_dir / fixture_name
                if not fixture_path.is_file():
                    continue
                with open(fixture_path, encoding="utf-8") as handle:
                    raw_state = json.load(handle)
                loader = tolerant_state_loading_test_support.make_loader(
                    collection,
                    state_class,
                    **loader_kwargs,
                )
                parsed_state = loader.from_dict(raw_state)
                assert parsed_state is not None

    def test_loads_legacy_ad_hoc_fixtures_via_tolerant_loader(self):
        wire_dir = openapi_compat_lib.wire_root_dir()
        ad_hoc_dir = wire_dir / "legacy" / "ad_hoc"
        if not ad_hoc_dir.is_dir():
            return
        for fixture_path in sorted(ad_hoc_dir.glob("*.json")):
            expectation_key = SYNC_LEGACY_AD_HOC_EXPECTATIONS.get(fixture_path.name)
            assert expectation_key is not None, (
                f"Unregistered legacy/ad_hoc fixture: {fixture_path.name}"
            )
            with open(fixture_path, encoding="utf-8") as handle:
                fixture_payload = json.load(handle)
            if expectation_key == "strategies_state_with_single_strategy":
                loader = tolerant_state_loading_test_support.make_loader(
                    "user-strategies",
                    protocol_models.StrategiesState,
                    **tolerant_state_loading_test_support.strategy_tolerant_loading_kwargs(),
                )
                parsed_state = loader.from_dict(fixture_payload)
                assert parsed_state is not None
            elif expectation_key == "user_action":
                parsed_action = protocol_models.UserAction.from_dict(fixture_payload)
                assert parsed_action is not None
            else:
                raise ValueError(f"Unknown sync legacy ad_hoc expectation: {expectation_key}")
