#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.

import decimal
import json

import mock
import pytest

import octobot.storage.process_bot_state_dumper as process_bot_state_dumper_import
import octobot_flow.entities.accounts.exchange_account_elements as exchange_account_elements_import
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.exchanges as trading_exchanges


def _order_stub(exchange_order_id: str) -> dict:
    return {
        trading_constants.STORAGE_ORIGIN_VALUE: {
            trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value: exchange_order_id,
        }
    }


class TestWriteStateFileAsync:
    @pytest.mark.asyncio
    async def test_writes_json_when_orders_contain_decimal(self, tmp_path):
        elements = exchange_account_elements_import.ExchangeAccountElements(
            name="binance",
            orders=trading_exchanges.OrdersDetails(
                open_orders=[
                    {
                        "price": decimal.Decimal("1.0001"),
                        "quantity": decimal.Decimal("50"),
                        "symbol": "USDC/USDT",
                    }
                ],
            ),
        )
        state_file = tmp_path / "bot_state.json"
        with mock.patch.object(
            process_bot_state_dumper_import,
            "_synced_aggregated_exchange_account_elements",
            mock.Mock(return_value=elements),
        ):
            await process_bot_state_dumper_import._write_state_file_async(
                str(state_file),
                30.0,
                mock.Mock(),
            )
        parsed = json.loads(state_file.read_text(encoding="utf-8"))
        order = parsed["exchange_account_elements"]["orders"]["open_orders"][0]
        assert order["price"] == 1.0001
        assert order["quantity"] == 50.0
        assert isinstance(order["price"], float)
        assert isinstance(order["quantity"], float)


class TestSyncedAggregatedExchangeAccountElements:
    def test_aggregates_all_trading_exchanges(self):
        binance_manager = mock.Mock()
        okx_manager = mock.Mock()

        def _sync_from_exchange_manager(self, exchange_manager, _transactions):
            if exchange_manager is binance_manager:
                self.name = "binanceus"
                self.orders = trading_exchanges.OrdersDetails(
                    open_orders=[_order_stub("binance-order")]
                )
                return []
            if exchange_manager is okx_manager:
                self.name = "okx"
                self.orders = trading_exchanges.OrdersDetails(
                    open_orders=[_order_stub("okx-order")]
                )
                return []
            raise AssertionError("unexpected exchange manager")

        with (
            mock.patch(
                "octobot.storage.process_bot_state_dumper.trading_api.get_exchange_manager_from_exchange_id",
                side_effect=[binance_manager, okx_manager],
            ),
            mock.patch(
                "octobot.storage.process_bot_state_dumper.trading_api.get_trading_exchanges",
                return_value=[binance_manager, okx_manager],
            ),
            mock.patch(
                "octobot.storage.process_bot_state_dumper.trading_api.get_exchange_name",
                side_effect=lambda manager: "binanceus" if manager is binance_manager else "okx",
            ),
            mock.patch.object(
                exchange_account_elements_import.ExchangeAccountElements,
                "sync_from_exchange_manager",
                _sync_from_exchange_manager,
            ),
        ):
            octobot = mock.Mock()
            octobot.exchange_producer.exchange_manager_ids = ["binance-id", "okx-id"]
            aggregated = process_bot_state_dumper_import._synced_aggregated_exchange_account_elements(octobot)

        assert aggregated.name == "binanceus,okx"
        assert len(aggregated.orders.open_orders) == 2
