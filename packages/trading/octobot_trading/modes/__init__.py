# pylint: disable=E0611, E0401
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

from octobot_trading.modes import abstract_trading_mode
from octobot_trading.modes.abstract_trading_mode import (
    AbstractTradingMode,
)

from octobot_trading.modes import channel
from octobot_trading.modes.channel import (
    check_factor,
    ModeChannelConsumer,
    ModeChannelProducer,
    ModeChannel,
    AbstractTradingModeConsumer,
    AbstractTradingModeProducer,
)

from octobot_trading.modes import scripted_trading_mode
from octobot_trading.modes.scripted_trading_mode import (
    AbstractScriptedTradingMode,
    AbstractScriptedTradingModeProducer,
)

from octobot_trading.modes import script_keywords
from octobot_trading.modes.script_keywords import (
    Context,
)

from octobot_trading.modes import mode_config
from octobot_trading.modes.mode_config import (
    get_activated_trading_mode,
    should_emit_trading_signals_user_input,
    is_trading_signal_emitter,
    user_select_order_amount,
    get_order_amount_value_desc,
    get_user_selected_order_amount,
)

from octobot_trading.modes import modes_factory
from octobot_trading.modes.modes_factory import (
    create_trading_modes,
    create_trading_mode,
    create_temporary_trading_mode_with_local_config,
)

from octobot_trading.modes import mode_activity
from octobot_trading.modes.mode_activity import (
    TradingModeActivity,
)

from octobot_trading.modes import modes_util
from octobot_trading.modes.modes_util import (
    get_required_candles_count,
    get_assets_requiring_extra_price_data_to_convert,
    convert_assets_to_target_asset,
    convert_asset_to_target_asset,
    get_instantly_filled_limit_order_adapted_price,
    get_instantly_filled_limit_order_adapted_price_and_quantity,
    notify_portfolio_optimization_complete,
    get_trading_modes_of_this_type_on_this_matrix,
    enabled_trader_only,
)

__all__ = [
    "ModeChannelConsumer",
    "ModeChannelProducer",
    "ModeChannel",
    "AbstractTradingModeProducer",
    "AbstractTradingMode",
    "AbstractTradingModeConsumer",
    "AbstractScriptedTradingMode",
    "AbstractScriptedTradingModeProducer",
    "Context",
    "check_factor",
    "create_trading_modes",
    "create_trading_mode",
    "create_temporary_trading_mode_with_local_config",
    "TradingModeActivity",
    "get_activated_trading_mode",
    "should_emit_trading_signals_user_input",
    "is_trading_signal_emitter",
    "user_select_order_amount",
    "get_order_amount_value_desc",
    "get_user_selected_order_amount",
    "get_required_candles_count",
    "get_assets_requiring_extra_price_data_to_convert",
    "convert_assets_to_target_asset",
    "convert_asset_to_target_asset",
    "get_instantly_filled_limit_order_adapted_price",
    "get_instantly_filled_limit_order_adapted_price_and_quantity",
    "notify_portfolio_optimization_complete",
    "get_trading_modes_of_this_type_on_this_matrix",
    "enabled_trader_only",
]
