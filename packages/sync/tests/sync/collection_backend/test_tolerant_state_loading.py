#  Drakkar-Software OctoBot-Sync
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.

import enum
import json
import typing

import pydantic
import pytest

import octobot_protocol.models as protocol_models
import octobot_sync.crypto as sync_crypto
import octobot_sync.sync.collection_backend.base_local_collection_storage as base_storage_module
import octobot_sync.sync.collection_backend.errors as collection_errors
import octobot_sync.sync.collection_backend.tolerant_state_loading as tolerant_state_loading_module
import octobot_sync.sync.collection_providers.user_strategy_provider as strategy_provider_module
import octobot_protocol.models.strategy_configuration as protocol_strategy_configuration


_TEST_ADDRESS = "0xaaabbbcccddd"
_TEST_PRIVATE_KEY = "private-key"


class TestItemStatus(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class TestItemModel(pydantic.BaseModel):
    id: str
    status: TestItemStatus

    def to_json(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_json(cls, json_str: str) -> typing.Optional["TestItemModel"]:
        return cls.model_validate_json(json_str)


class TestStateModel(pydantic.BaseModel):
    version: str
    items: typing.Optional[list[TestItemModel]] = None

    def to_json(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_json(cls, json_str: str) -> typing.Optional["TestStateModel"]:
        return cls.model_validate_json(json_str)


def _valid_trading_tentacles_strategy_dict() -> dict[str, typing.Any]:
    return {
        "id": "strat-valid",
        "version": "1",
        "reference_market": "USDC",
        "configuration": {
            "configuration_type": "trading_tentacles",
            "name": "DCATradingMode",
            "config": {"trading_pairs": ["BTC/USDC"]},
            "symbols": ["BTC/USDC"],
        },
    }


def _legacy_grid_strategy_dict() -> dict[str, typing.Any]:
    return {
        "id": "strat-legacy",
        "version": "1",
        "reference_market": "USDC",
        "configuration": {
            "configuration_type": "grid",
            "pair_settings": None,
            "name": None,
            "config": None,
        },
    }


def _strategy_tolerant_loading_kwargs() -> dict[str, typing.Any]:
    return {
        "model_sanitizers": strategy_provider_module.StrategyProvider.MODEL_SANITIZERS,
        "model_fallbacks": strategy_provider_module.StrategyProvider.MODEL_FALLBACKS,
    }


def _make_loader(
    collection: str,
    state_class: typing.Any = None,
    **loader_kwargs: typing.Any,
) -> tolerant_state_loading_module.TolerantStateLoader:
    return tolerant_state_loading_module.TolerantStateLoader(
        state_class,
        collection=collection,
        **loader_kwargs,
    )


class TestSanitizeStrategyConfigurationDict:
    def test_removes_invalid_configuration_type(self):
        sanitize = strategy_provider_module.StrategyProvider.MODEL_SANITIZERS[
            protocol_strategy_configuration.StrategyConfiguration
        ]
        sanitized = sanitize({"configuration_type": "grid", "name": "GridTradingMode"})
        assert "configuration_type" not in sanitized
        assert sanitized["name"] == "GridTradingMode"

    def test_removes_none_values(self):
        sanitize = strategy_provider_module.StrategyProvider.MODEL_SANITIZERS[
            protocol_strategy_configuration.StrategyConfiguration
        ]
        sanitized = sanitize(
            {"configuration_type": "trading_tentacles", "name": None, "config": {}},
        )
        assert sanitized == {
            "configuration_type": "trading_tentacles",
            "config": {},
        }


class TestModelFromDictLenient:
    def test_returns_valid_strategy_unchanged(self):
        loader = _make_loader("test", **_strategy_tolerant_loading_kwargs())
        parsed_strategy = loader.model_from_dict_lenient(
            protocol_models.Strategy,
            _valid_trading_tentacles_strategy_dict(),
            context="test.strategies",
            allow_skip=False,
        )
        assert parsed_strategy is not None
        assert parsed_strategy.id == "strat-valid"
        assert parsed_strategy.configuration.actual_instance is not None
        assert (
            parsed_strategy.configuration.actual_instance.configuration_type
            == protocol_models.ActionConfigurationType.TRADING_TENTACLES
        )

    def test_legacy_grid_configuration_uses_empty_shell(self):
        loader = _make_loader("test", **_strategy_tolerant_loading_kwargs())
        parsed_strategy = loader.model_from_dict_lenient(
            protocol_models.Strategy,
            _legacy_grid_strategy_dict(),
            context="test.strategies",
            allow_skip=False,
        )
        assert parsed_strategy is not None
        assert parsed_strategy.id == "strat-legacy"
        assert parsed_strategy.configuration.actual_instance is None

    def test_invalid_enum_item_is_skipped_when_allowed(self):
        loader = _make_loader("test")
        parsed_item = loader.model_from_dict_lenient(
            TestItemModel,
            {"id": "item-1", "status": "unknown-status"},
            context="test.items",
            allow_skip=True,
        )
        assert parsed_item is None


class TestStateFromDictLenient:
    def test_valid_state_round_trips(self):
        raw_state = {
            "version": "1.0.0",
            "strategies": [_valid_trading_tentacles_strategy_dict()],
        }
        loader = _make_loader(
            "user-strategies",
            protocol_models.StrategiesState,
            **_strategy_tolerant_loading_kwargs(),
        )
        parsed_state = loader.from_dict(raw_state)
        assert parsed_state is not None
        assert len(parsed_state.strategies) == 1
        assert parsed_state.strategies[0].id == "strat-valid"

    def test_mixed_valid_and_legacy_strategies_load(self):
        raw_state = {
            "version": "1.0.0",
            "strategies": [
                _valid_trading_tentacles_strategy_dict(),
                _legacy_grid_strategy_dict(),
            ],
        }
        loader = _make_loader(
            "user-strategies",
            protocol_models.StrategiesState,
            **_strategy_tolerant_loading_kwargs(),
        )
        parsed_state = loader.from_dict(raw_state)
        assert parsed_state is not None
        assert len(parsed_state.strategies) == 2
        assert parsed_state.strategies[0].id == "strat-valid"
        assert parsed_state.strategies[1].id == "strat-legacy"
        assert parsed_state.strategies[1].configuration.actual_instance is None

    def test_one_invalid_test_item_preserves_valid_siblings(self):
        raw_state = {
            "version": "1.0.0",
            "items": [
                {"id": "item-valid", "status": "active"},
                {"id": "item-invalid", "status": "unknown-status"},
            ],
        }
        loader = _make_loader("test-items", TestStateModel)
        parsed_state = loader.from_dict(raw_state)
        assert parsed_state is not None
        assert len(parsed_state.items) == 1
        assert parsed_state.items[0].id == "item-valid"

    def test_accounts_state_skips_invalid_exchange_config(self):
        raw_state = {
            "version": "1.0.0",
            "accounts": [],
            "exchange_configs": [
                {
                    "id": "cfg-valid",
                    "name": "Binance",
                    "exchange": "binance",
                    "sandboxed": False,
                },
                {
                    "name": "Broken",
                    "exchange": "binance",
                    "sandboxed": False,
                },
            ],
        }
        loader = _make_loader("user-accounts", protocol_models.AccountsState)
        parsed_state = loader.from_dict(raw_state)
        assert parsed_state is not None
        assert parsed_state.exchange_configs is not None
        assert len(parsed_state.exchange_configs) == 1
        assert parsed_state.exchange_configs[0].id == "cfg-valid"


class TestStateFromJsonLenient:
    def test_parses_json_string(self):
        raw_state = {
            "version": "1.0.0",
            "strategies": [_legacy_grid_strategy_dict()],
        }
        loader = _make_loader(
            "user-strategies",
            protocol_models.StrategiesState,
            **_strategy_tolerant_loading_kwargs(),
        )
        parsed_state = loader.from_json(json.dumps(raw_state))
        assert parsed_state.strategies[0].configuration.actual_instance is None


class TestBaseLocalCollectionStorageTolerantLoad:
    def _make_storage(self, tmp_path):
        return base_storage_module.BaseLocalCollectionStorage(
            collection="user-strategies",
            base_folder=str(tmp_path),
        )

    def test_encrypted_legacy_strategy_state_loads_without_error(self, tmp_path):
        storage = self._make_storage(tmp_path)
        legacy_state_json = json.dumps(
            {
                "version": "1.0.0",
                "strategies": [_legacy_grid_strategy_dict()],
            }
        )
        blob = sync_crypto.encrypt_bytes_to_blob_dict(
            legacy_state_json.encode("utf-8"),
            _TEST_PRIVATE_KEY,
            "user-strategies",
        )
        path = tmp_path / "user-strategies" / f"{_TEST_ADDRESS}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(blob, handle)

        loaded_state = storage.load_state(
            _TEST_ADDRESS,
            _TEST_PRIVATE_KEY,
            protocol_models.StrategiesState,
            model_sanitizers=strategy_provider_module.StrategyProvider.MODEL_SANITIZERS,
            model_fallbacks=strategy_provider_module.StrategyProvider.MODEL_FALLBACKS,
        )
        assert loaded_state.strategies is not None
        assert len(loaded_state.strategies) == 1
        assert loaded_state.strategies[0].id == "strat-legacy"
        assert loaded_state.strategies[0].configuration.actual_instance is None

    def test_strict_load_rejects_legacy_strategy_state(self, tmp_path):
        storage = self._make_storage(tmp_path)
        legacy_state_json = json.dumps(
            {
                "version": "1.0.0",
                "strategies": [_legacy_grid_strategy_dict()],
            }
        )
        blob = sync_crypto.encrypt_bytes_to_blob_dict(
            legacy_state_json.encode("utf-8"),
            _TEST_PRIVATE_KEY,
            "user-strategies",
        )
        path = tmp_path / "user-strategies" / f"{_TEST_ADDRESS}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(blob, handle)

        with pytest.raises(collection_errors.CollectionFileFormatError):
            storage.load_state(
                _TEST_ADDRESS,
                _TEST_PRIVATE_KEY,
                protocol_models.StrategiesState,
                strict=True,
            )
