#  Drakkar-Software OctoBot-Tentacles
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  Named socket_namespaces so the parent websockets package can expose `namespaces` as the
#  ordered notifier list without shadowing this subpackage for imports like
#  `...socket_namespaces.dashboard`.

import tentacles.Services.Interfaces.web_interface.websockets.socket_namespaces.backtesting as backtesting
import tentacles.Services.Interfaces.web_interface.websockets.socket_namespaces.data_collector as data_collector
import tentacles.Services.Interfaces.web_interface.websockets.socket_namespaces.dashboard as dashboard
import tentacles.Services.Interfaces.web_interface.websockets.socket_namespaces.notifications as notifications
import tentacles.Services.Interfaces.web_interface.websockets.socket_namespaces.social_data_collector as social_data_collector
import tentacles.Services.Interfaces.web_interface.websockets.socket_namespaces.strategy_optimizer as strategy_optimizer

namespaces = [
    data_collector.notifier,
    social_data_collector.notifier,
    backtesting.notifier,
    dashboard.notifier,
    notifications.notifier,
    strategy_optimizer.notifier,
]

__all__ = ["namespaces"]
