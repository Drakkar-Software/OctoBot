#  Drakkar-Software OctoBot-Flow
#  Copyright (c) Drakkar-Software, All rights reserved.

import copy

import octobot_trading.constants as trading_constants
import octobot_trading.enums as trading_enums
import octobot_trading.exchanges.util.exchange_data as exchange_data_import


class GlobalViewRefreshedElements:
    def __init__(self, exchange_data: exchange_data_import.ExchangeData, save_copy: bool = True):
        self.open_orders: list[dict] = (
            copy.deepcopy(exchange_data.orders_details.open_orders) if save_copy else list(
                exchange_data.orders_details.open_orders or []
            )
        ) if exchange_data.orders_details.open_orders else []
        self.portfolio: dict[str, dict] = (
            copy.deepcopy(exchange_data.portfolio_details.content) if save_copy else dict(
                exchange_data.portfolio_details.content or {}
            )
        ) if exchange_data.portfolio_details else {}

    def confirmed_change(
        self, exchange_data: exchange_data_import.ExchangeData
    ) -> bool:
        return self._confirmed_change(GlobalViewRefreshedElements(exchange_data, save_copy=False))

    def _confirmed_change(
        self, other_global_view_refreshed_elements: "GlobalViewRefreshedElements"
    ) -> bool:
        if self._get_orders_signature(self.open_orders) != self._get_orders_signature(
            other_global_view_refreshed_elements.open_orders
        ):
            return True
        if self._get_portfolio_signature(self.portfolio) != self._get_portfolio_signature(
            other_global_view_refreshed_elements.portfolio
        ):
            return True
        return False

    def _get_orders_signature(self, orders: list[dict]) -> str:
        return ",".join(sorted([
            self._get_order_signature(order) for order in orders
        ]))

    def _get_order_signature(self, order: dict) -> str:
        try:
            origin_value = order[trading_constants.STORAGE_ORIGIN_VALUE]
        except KeyError:
            return ""
        return (
            f"{origin_value.get(trading_enums.ExchangeConstantsOrderColumns.EXCHANGE_ID.value, '')}"
            f"_{origin_value.get(trading_enums.ExchangeConstantsOrderColumns.FILLED.value, 0)}"
        )

    def _get_portfolio_signature(self, portfolio: dict[str, dict]) -> str:
        return ",".join(sorted([
            f"{asset}:{value}" for asset, value in portfolio.items()
        ]))
