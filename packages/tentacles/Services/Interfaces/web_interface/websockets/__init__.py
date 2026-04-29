#  Drakkar-Software OctoBot-Tentacles
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


namespaces = []


from tentacles.Services.Interfaces.web_interface.websockets import abstract_websocket_namespace_notifier
from tentacles.Services.Interfaces.web_interface.websockets.abstract_websocket_namespace_notifier import (
    AbstractWebSocketNamespaceNotifier,
    websocket_with_login_required_when_activated,
)

from tentacles.Services.Interfaces.web_interface.websockets import data_collector
from tentacles.Services.Interfaces.web_interface.websockets import social_data_collector
from tentacles.Services.Interfaces.web_interface.websockets import backtesting
from tentacles.Services.Interfaces.web_interface.websockets import dashboard
from tentacles.Services.Interfaces.web_interface.websockets import notifications
from tentacles.Services.Interfaces.web_interface.websockets import strategy_optimizer


from tentacles.Services.Interfaces.web_interface.websockets.data_collector import (
    DataCollectorNamespace,
)
from tentacles.Services.Interfaces.web_interface.websockets.social_data_collector import (
    SocialDataCollectorNamespace,
)
from tentacles.Services.Interfaces.web_interface.websockets.backtesting import (
    BacktestingNamespace,
)
from tentacles.Services.Interfaces.web_interface.websockets.dashboard import (
    DashboardNamespace,
)
from tentacles.Services.Interfaces.web_interface.websockets.notifications import (
    NotificationsNamespace,
)
from tentacles.Services.Interfaces.web_interface.websockets.strategy_optimizer import (
    StrategyOptimizerNamespace,
)


__all__ = [
    "AbstractWebSocketNamespaceNotifier",
    "websocket_with_login_required_when_activated",
    "BacktestingNamespace",
    "DataCollectorNamespace",
    "SocialDataCollectorNamespace",
    "DashboardNamespace",
    "NotificationsNamespace",
    "StrategyOptimizerNamespace",
]
