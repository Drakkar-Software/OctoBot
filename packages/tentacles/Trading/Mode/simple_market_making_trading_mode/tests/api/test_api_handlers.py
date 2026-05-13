#  Drakkar-Software OctoBot-Tentacles
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  Integration tests for market-making API handlers (real public exchange data; no exchange mocks).

import asyncio
import os
import threading
import typing

import mock
import pytest

import octobot_commons.symbols.symbol_util as commons_symbols
import octobot_commons.asyncio_tools
import octobot_protocol.models.market_making_configuration as market_making_configuration_model

import tentacles.Trading.Mode.simple_market_making_trading_mode.api.api_handlers as api_handlers
import tentacles.Trading.Mode.simple_market_making_trading_mode.api.constants as api_constants
import tentacles.Trading.Mode.simple_market_making_trading_mode.api.models as models
import tentacles.Services.Interfaces.node_api_interface.core.exchanges as exchanges_core


def is_on_github_ci() -> bool:
    return bool(os.getenv("GITHUB_ACTIONS"))


# binanceus works on GitHub CI; binance is used for local runs.
EXCHANGE_INTERNAL_NAME = "binanceus" if is_on_github_ci() else "binance"
LIQUID_TEST_SYMBOL = "BTC/USDT"


def _raw_exchange_for_dispatch() -> dict:
    return {
        "name": EXCHANGE_INTERNAL_NAME,
        "exchange_type": "spot",
    }


def _normalized_exchange_configs() -> list:
    return [
        exchanges_core.ExchangeConfig.model_validate(
            {
                "name": EXCHANGE_INTERNAL_NAME,
                "exchange_type": "spot",
                "sandboxed": False,
                "url": "",
            }
        )
    ]


def _minimal_market_making_configuration() -> market_making_configuration_model.MarketMakingConfiguration:
    return market_making_configuration_model.MarketMakingConfiguration.model_validate(
        {
            "configuration_type": "market_making",
            "pair_settings": [
                {
                    "trading_pair": LIQUID_TEST_SYMBOL,
                    "exchange": EXCHANGE_INTERNAL_NAME,
                    "reference_price": [
                        {
                            "exchange": EXCHANGE_INTERNAL_NAME,
                            "formula": "",
                            "pair": LIQUID_TEST_SYMBOL,
                            "weight": 1,
                        }
                    ],
                    "min_spread": 5,
                    "max_spread": 20,
                    "order_book_depth": {
                        "cumulated_volume_percent": 6,
                        "percent_daily_trading_volume": 1,
                    },
                    "bids_count": 5,
                    "asks_count": 5,
                    "orders_distribution": "linear",
                    "funds_distribution": "flat",
                    "max_base_budget": 0,
                    "max_quote_budget": 0,
                    "min_base_budget": 100000,
                    "min_quote_budget": 1000,
                }
            ],
        }
    )


def _run_background_fingerprint_inline_for_test(
    capture: dict[str, typing.Any],
) -> typing.Callable[[str, typing.Any], bool]:
    """
    Same idea as ``BackgroundFingerprintAsyncExecutor`` (``asyncio.run`` in a thread),
    but blocks until the coroutine ends so tests can read ``core.update_liquidity_scores``'s
    return value (the dispatch handler would otherwise not await it).
    """

    def _run_background_fingerprint_async_executor(
        fingerprint: str, coroutine,
    ) -> bool:
        def _worker() -> None:
            try:
                capture["update_liquidity_scores_result"] = asyncio.run(coroutine)
            except Exception as error:
                capture["update_liquidity_scores_error"] = error

        worker_thread = threading.Thread(
            target=_worker, name="test-run-background-liquidity-scores"
        )
        worker_thread.start()
        worker_thread.join(timeout=600)
        if worker_thread.is_alive():
            raise AssertionError(
                "core.update_liquidity_scores did not complete within 600 seconds"
            )
        if "update_liquidity_scores_error" in capture:
            raise capture["update_liquidity_scores_error"]
        return True

    return _run_background_fingerprint_async_executor


pytestmark = pytest.mark.asyncio


class TestComputeMarketMakingVolume:
    async def test_volume_by_symbol_structure(self):
        result = await api_handlers.compute_market_making_volume(
            _normalized_exchange_configs(),
            _minimal_market_making_configuration(),
            None,
        )
        assert EXCHANGE_INTERNAL_NAME in result
        by_symbol = result[EXCHANGE_INTERNAL_NAME]
        assert len(by_symbol) == 1
        assert LIQUID_TEST_SYMBOL in by_symbol
        per_symbol = by_symbol[LIQUID_TEST_SYMBOL]
        assert api_constants.VOLUME_KEY in per_symbol
        assert api_constants.ERROR_KEY in per_symbol
        if per_symbol[api_constants.ERROR_KEY]:
            pytest.fail(
                f"expected no error for {LIQUID_TEST_SYMBOL}, got {per_symbol[api_constants.ERROR_KEY]}"
            )
        assert isinstance(per_symbol[api_constants.VOLUME_KEY], dict)
        base, quote = commons_symbols.parse_symbol(LIQUID_TEST_SYMBOL).base_and_quote()
        assert per_symbol[api_constants.VOLUME_KEY][base] > 0
        assert per_symbol[api_constants.VOLUME_KEY][quote] > 0

    async def test_volume_empty_config_raises(self):
        with pytest.raises(ValueError):
            await api_handlers.compute_market_making_volume(
                _normalized_exchange_configs(), None, None
            )

    async def test_dispatch_market_making_volume_empty_config_returns_400(self):
        data = {
            "type": "market_making_volume",
            "exchanges": [_raw_exchange_for_dispatch()],
            "config": {"config": {}},
        }
        body, status = await api_handlers.dispatch_market_making_request(data)
        assert status == 400
        assert body["error"]


class TestGetPriceAndPredictedOrderBook:
    async def test_predicted_order_book_has_price_bids_asks(self):
        result = await api_handlers.get_price_and_predicted_order_book(
            _normalized_exchange_configs(),
            _minimal_market_making_configuration(),
            None,
        )
        assert EXCHANGE_INTERNAL_NAME in result
        by_symbol = result[EXCHANGE_INTERNAL_NAME]
        assert LIQUID_TEST_SYMBOL in by_symbol
        ob = by_symbol[LIQUID_TEST_SYMBOL]
        if api_constants.ERROR_KEY in ob:
            pytest.fail(f"unexpected order book error: {ob[api_constants.ERROR_KEY]}")
        assert ob[api_constants.PRICE_KEY] > 0
        assert isinstance(ob[api_constants.BIDS_KEY], list)
        assert isinstance(ob[api_constants.ASKS_KEY], list)
        assert len(ob[api_constants.BIDS_KEY]) > 0
        assert len(ob[api_constants.ASKS_KEY]) > 0
        first_bid = ob[api_constants.BIDS_KEY][0]
        for key in (api_constants.PRICE_KEY, api_constants.AMOUNT_KEY, api_constants.TOTAL_KEY):
            assert key in first_bid

    async def test_predicted_order_book_empty_config_raises(self):
        with pytest.raises(ValueError):
            await api_handlers.get_price_and_predicted_order_book(
                _normalized_exchange_configs(), None, None
            )

    async def test_dispatch_predicted_order_book_empty_config_returns_400(self):
        data = {
            "type": "predicted_order_book",
            "exchanges": [_raw_exchange_for_dispatch()],
            "config": {"config": {}},
        }
        body, status = await api_handlers.dispatch_market_making_request(data)
        assert status == 400
        assert body["error"]


class TestUpdateLiquidityScore:
    async def test_dispatch_invalid_policy_returns_404(self):
        data = {
            "type": "update_liquidity_score",
            "exchanges": [_raw_exchange_for_dispatch()],
            "policy": "__invalid__",
            "symbols": [LIQUID_TEST_SYMBOL],
        }
        body, status = await api_handlers.dispatch_market_making_request(data)
        assert status == 404
        assert isinstance(body, dict)
        assert "error" in body
        # `dispatch_market_making_request` maps `policy` to `OrderBookFetchPolicy` before
        # `update_liquidity_score` (which uses `core.update_liquidity_scores` in the background).
        error_text = str(body["error"])
        assert error_text
        assert "OrderBookFetchPolicy" in error_text

    async def test_dispatch_update_liquidity_score_success(self) -> None:
        data = {
            "type": "update_liquidity_score",
            "exchanges": [_raw_exchange_for_dispatch()],
            "symbols": [LIQUID_TEST_SYMBOL],
        }
        inline_capture: dict[str, typing.Any] = {}
        with mock.patch.object(
            octobot_commons.asyncio_tools, "run_background_fingerprint_async_executor",
            _run_background_fingerprint_inline_for_test(inline_capture),
        ):
            body, status = await api_handlers.dispatch_market_making_request(data)
        assert status == 200
        assert body == "update scheduled"
        liquidity_scores = inline_capture["update_liquidity_scores_result"]
        assert isinstance(liquidity_scores, list)
        assert len(liquidity_scores) == 1
        for liquidity_score in liquidity_scores:
            assert isinstance(liquidity_score, models.LiquidityScore)
            assert liquidity_score.symbol == LIQUID_TEST_SYMBOL
            assert liquidity_score.exchange_id
            assert 0 < liquidity_score.score <= 10
            assert liquidity_score.bid_ask_spread is not None
            assert 0 < liquidity_score.bid_ask_spread < 99999
            assert liquidity_score.bids_ob_depth is not None
            assert 0 < liquidity_score.bids_ob_depth <= 10
            assert liquidity_score.asks_ob_depth is not None
            assert 0 < liquidity_score.asks_ob_depth <= 10


class TestDispatchMarketMakingRequest:
    async def test_unknown_request_type_returns_400(self):
        request_type = "not_a_real_request_type"
        data = {"type": request_type, "exchanges": [_raw_exchange_for_dispatch()]}
        body, status = await api_handlers.dispatch_market_making_request(data)
        assert status == 400
        assert body == f"unknown request_type: {request_type}"

    async def test_missing_type_returns_400(self):
        data: dict[str, typing.Any] = {}
        body, status = await api_handlers.dispatch_market_making_request(data)
        assert status == 400
        assert body == "unknown request_type: None"

    async def test_exchanges_only_no_type_still_400(self):
        data = {"exchanges": [_raw_exchange_for_dispatch()]}
        body, status = await api_handlers.dispatch_market_making_request(data)
        assert status == 400
        assert body == "unknown request_type: None"

    async def test_market_making_volume_invalid_config_returns_400(self):
        invalid_market_making_payload = {
            "configuration_type": "market_making",
            "pair_settings": [
                {
                    "trading_pair": LIQUID_TEST_SYMBOL,
                    "exchange": EXCHANGE_INTERNAL_NAME,
                    # required "reference_price" key intentionally missing
                    "min_spread": 0.5,
                    "max_spread": 1.0,
                    "bids_count": 5,
                    "asks_count": 5,
                    "orders_distribution": "linear",
                    "funds_distribution": "flat",
                }
            ],
        }
        response_body, response_status = await api_handlers.dispatch_market_making_request(
            {
                "type": "market_making_volume",
                "exchanges": [_raw_exchange_for_dispatch()],
                "config": {"config": invalid_market_making_payload},
            }
        )
        assert response_status == 400
        assert isinstance(response_body, dict)
        assert "error" in response_body
        assert "Invalid market making config" in response_body["error"]
