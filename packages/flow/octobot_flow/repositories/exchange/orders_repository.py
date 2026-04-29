import typing

import octobot_flow.repositories.exchange.base_exchange_repository as base_exchange_repository_import
import octobot_trading.util.test_tools.exchanges_test_tools as exchanges_test_tools_import
import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.storage as orders_storage
import octobot_trading.constants as trading_constants
import octobot_trading.personal_data as trading_personal_data


class OrdersRepository(base_exchange_repository_import.BaseExchangeRepository):

    async def fetch_open_orders(
        self, symbols: list[str], ignore_unsupported_orders: bool = True
    ) -> list[dict]:
        if not symbols:
            return []
        updater = typing.cast(
            trading_personal_data.OrdersUpdater,
            self.get_channel_updater(trading_constants.ORDERS_CHANNEL)
        )
        open_orders = await updater.fetch_open_orders(symbols)
        return [
            exchanges_test_tools_import.parse_order_into_dict(
                self.exchange_manager, order, True, ignore_unsupported_orders
            )
            for order in open_orders
            if order
        ] # type: ignore

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