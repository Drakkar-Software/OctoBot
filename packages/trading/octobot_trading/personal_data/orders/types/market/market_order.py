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
import octobot_commons.logging
import octobot_trading.enums as enums
import octobot_trading.personal_data.orders.order as order_class


class MarketOrder(order_class.Order):
    SUPPORTS_GROUPING = False    # False when orders of this type can't be grouped
    USE_ORIGIN_QUANTITY_AS_FILLED_QUANTITY = True

    async def update_order_status(self, force_refresh=False):
        if not self.is_active:
            octobot_commons.logging.get_logger(self.logger_name).error(
                f"UNEXPECTED: a {self.get_name()} can't be inactive"
            )
            return
        if self.trader.simulate:
            # TODO: ensure no issue un not running it in task anymore
            await self.on_fill(force_fill=True)
            # asyncio.create_task(self.on_fill(force_fill=True))
            # # In trading simulation wait for the next asyncio loop iteration to ensure this order status
            # # is updated before leaving this method
            # await asyncio_tools.wait_asyncio_next_cycle()

    def on_fill_actions(self):
        self.taker_or_maker = enums.ExchangeConstantsMarketPropertyColumns.TAKER.value
        self.origin_price = self.created_last_price
        self.update_order_filled_values(self.created_last_price)
        order_class.Order.on_fill_actions(self)

    def _should_instant_fill(self):
        return True

    def can_be_edited(self):
        # instantly filled orders can't be edited
        return False

    def use_current_price_as_origin_price(self):
        # Override to return True when the current order price can't be set by the user (ex: market orders)
        return True

