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

from tentacles.Services.Interfaces.web_interface.websockets.core.abstract_websocket_namespace_notifier import (
    AbstractWebSocketNamespaceNotifier,
)
from tentacles.Services.Interfaces.web_interface.websockets.socket_namespaces import namespaces
from tentacles.Services.Interfaces.web_interface.websockets.socket_namespaces.backtesting import (
    BacktestingNamespace,
)
from tentacles.Services.Interfaces.web_interface.websockets.socket_namespaces.data_collector import (
    DataCollectorNamespace,
)
from tentacles.Services.Interfaces.web_interface.websockets.socket_namespaces.dashboard import (
    DashboardNamespace,
)
from tentacles.Services.Interfaces.web_interface.websockets.socket_namespaces.notifications import (
    NotificationsNamespace,
)
from tentacles.Services.Interfaces.web_interface.websockets.socket_namespaces.social_data_collector import (
    SocialDataCollectorNamespace,
)
from tentacles.Services.Interfaces.web_interface.websockets.socket_namespaces.strategy_optimizer import (
    StrategyOptimizerNamespace,
)
from tentacles.Services.Interfaces.web_interface.websockets.server.asgi_composite import build_composite_asgi_app


__all__ = [
    "AbstractWebSocketNamespaceNotifier",
    "BacktestingNamespace",
    "DataCollectorNamespace",
    "SocialDataCollectorNamespace",
    "DashboardNamespace",
    "NotificationsNamespace",
    "StrategyOptimizerNamespace",
    "build_composite_asgi_app",
    "namespaces",
]
