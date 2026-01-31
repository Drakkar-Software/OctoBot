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
import octobot_trading.personal_data.orders.states.pending_creation_order_state as pending_creation_order_state


class PendingCreationChainedOrderState(pending_creation_order_state.PendingCreationOrderState):
    def is_created(self) -> bool:
        """
        :return: True if the Order is created
        """
        # order is to be triggered as chained order: not created
        return False

    async def update(self) -> None:
        pass
