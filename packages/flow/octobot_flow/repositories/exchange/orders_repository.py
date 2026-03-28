import typing

import octobot_flow.repositories.exchange.base_exchange_repository as base_exchange_repository_import
import octobot_trading.util.test_tools.exchanges_test_tools as exchanges_test_tools_import
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.storage as orders_storage


class OrdersRepository(base_exchange_repository_import.BaseExchangeRepository):

    async def fetch_open_orders(
        self, symbols: list[str], ignore_unsupported_orders: bool = True
    ) -> list[dict]:
        if not symbols:
            return []
        return await exchanges_test_tools_import.get_open_orders(
            self.exchange_manager, None, symbols=symbols, ignore_unsupported_orders=ignore_unsupported_orders
        )

    def update_enriched_orders(
        self,
        updated_orders: list[dict[str, typing.Any]],
        existing_orders: dict[str, dict[str, dict[str, typing.Any]]]
    ) -> list[dict[str, typing.Any]]:
        account_orders_by_exchange_id = {
            order[trading_constants.STORAGE_ORIGIN_VALUE][trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value]: order
            for order in existing_orders
        }
        return [
            orders_storage.update_enriched_order(
                order,
                account_orders_by_exchange_id,
                self.exchange_manager
            )
            for order in updated_orders
        ]