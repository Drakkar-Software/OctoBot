#  Drakkar-Software OctoBot-Trading
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import typing
import decimal

import octobot_commons.symbols as symbol_util

import octobot_trading.constants as constants
import octobot_trading.errors as errors
import octobot_trading.enums as enums
import octobot_trading.personal_data.portfolios.portfolio_value_holder as portfolio_value_holder


class FuturesPortfolioValueHolder(portfolio_value_holder.PortfolioValueHolder):   
    def get_holdings_ratio(
        self, currency, traded_symbols_only=False, include_assets_in_open_orders=False, coins_whitelist=None
    ) -> typing.Optional[decimal.Decimal]:
        positions_manager = self.portfolio_manager.exchange_manager.exchange_personal_data.positions_manager
        total_portfolio_value: decimal.Decimal = self._get_total_holdings_value(
            coins_whitelist=coins_whitelist, traded_symbols_only=traded_symbols_only
        )

        if currency == self.portfolio_manager.reference_market:
            return self._get_holdings_ratio_from_portfolio(
                self.portfolio_manager.reference_market, traded_symbols_only=traded_symbols_only, coins_whitelist=coins_whitelist, include_assets_in_open_orders=include_assets_in_open_orders
            )

        currency_is_full_symbol = symbol_util.is_symbol(currency)
        symbol = currency
        if not currency_is_full_symbol:
            try:
                symbol = symbol_util.merge_currencies(currency, self.portfolio_manager.reference_market, settlement_asset=self.portfolio_manager.reference_market)
                position = positions_manager.get_symbol_position(symbol, enums.PositionSide.BOTH)
            except errors.ContractExistsError:
                # try to reverse the symbol
                symbol = symbol_util.merge_currencies(
                    self.portfolio_manager.reference_market, currency, settlement_asset=currency
                )
                position = positions_manager.get_symbol_position(symbol, enums.PositionSide.BOTH)
        else:
            position = positions_manager.get_symbol_position(symbol, enums.PositionSide.BOTH)

        if position.is_idle():
            position_value: decimal.Decimal = constants.ZERO
        else:
            # position.margin is in the settlement currency of the position
            # Convert it to the reference market for proper ratio calculation
            parsed_symbol = symbol_util.parse_symbol(symbol)
            settlement_currency = parsed_symbol.settlement_asset or parsed_symbol.quote
            position_value = self.value_converter.evaluate_value(
                settlement_currency, position.margin, init_price_fetchers=False
            )

        if include_assets_in_open_orders:
            if currency_is_full_symbol:
                # For full symbols get orders by exact symbol
                pending_order_value = self._get_open_orders_value_for_symbol(symbol)
                position_value += pending_order_value
            else:
                # For simple currencies (e.g., "ETH"), use currency-based matching
                pending_order_holdings = self._get_total_holdings_in_open_orders(currency)
                pending_order_value = self.value_converter.evaluate_value(
                    currency, pending_order_holdings, init_price_fetchers=False
                )
                position_value += pending_order_value

        return position_value / total_portfolio_value if total_portfolio_value > constants.ZERO else constants.ZERO