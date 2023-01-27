#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2023 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.

from octobot.automation.implementations.actions import send_notification
from octobot.automation.implementations.actions.send_notification import (
    SendNotification,
)
from octobot.automation.implementations.actions import cancel_open_orders
from octobot.automation.implementations.actions.cancel_open_orders import (
    CancelOpenOrders,
)
from octobot.automation.implementations.actions import sell_all_currencies
from octobot.automation.implementations.actions.sell_all_currencies import (
    SellAllCurrencies,
)
from octobot.automation.implementations.actions import stop_trading
from octobot.automation.implementations.actions.stop_trading import (
    StopTrading,
)

__all__ = [
    "SendNotification",
    "CancelOpenOrders",
    "SellAllCurrencies",
    "StopTrading",
]
