#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.

import decimal
import json

import mock
import pytest

import octobot.storage.process_bot_state_dumper as process_bot_state_dumper_import
import octobot_flow.entities.accounts.exchange_account_elements as exchange_account_elements_import
import octobot_trading.exchanges as trading_exchanges


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
            "_synced_exchange_account_elements_for_first_trading_exchange",
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
