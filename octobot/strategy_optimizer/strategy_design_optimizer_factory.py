#  Drakkar-Software OctoBot
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
import octobot_commons.tentacles_management.class_inspector as class_inspector
import octobot.strategy_optimizer.strategy_design_optimizer as strategy_design_optimizer


def create_most_advanced_strategy_design_optimizer(
        trading_mode, config, tentacles_setup_config, optimizer_settings=None
):
    advanced_class = strategy_design_optimizer.StrategyDesignOptimizer
    optimizer_classes = [
        optimizer_class
        for optimizer_class in class_inspector.get_all_classes_from_parent(advanced_class)
        if optimizer_class.ALLOWED_IN_FACTORY
    ]
    if optimizer_classes:
        # the last one of the list is the most advanced one
        advanced_class = optimizer_classes[-1]
    return advanced_class(trading_mode, config, tentacles_setup_config, optimizer_settings=optimizer_settings)
