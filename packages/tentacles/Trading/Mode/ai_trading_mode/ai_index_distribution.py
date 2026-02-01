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

import decimal

import tentacles.Trading.Mode.index_trading_mode.index_distribution as index_distribution

from tentacles.Agent.sub_agents.distribution_agent.constants import (
    INSTRUCTION_ACTION,
    INSTRUCTION_SYMBOL,
    INSTRUCTION_AMOUNT,
    INSTRUCTION_WEIGHT,
    ACTION_REDUCE_EXPOSURE,
    ACTION_INCREASE_EXPOSURE,
    ACTION_ADD_TO_DISTRIBUTION,
    ACTION_REMOVE_FROM_DISTRIBUTION,
    ACTION_UPDATE_RATIO,
    ACTION_INCREASE_FIAT_RATIO,
    ACTION_DECREASE_FIAT_RATIO,
)


def apply_ai_instructions(trading_mode, instructions: list):
    """
    Apply AI-generated instructions to update the portfolio distribution.
    """
    try:
        current_distribution = {}
        total_weight = decimal.Decimal(0)

        # Start with current distribution
        if trading_mode.ratio_per_asset:
            for asset, item in trading_mode.ratio_per_asset.items():
                current_distribution[asset] = item[
                    index_distribution.DISTRIBUTION_VALUE
                ]
                total_weight += decimal.Decimal(str(item[index_distribution.DISTRIBUTION_VALUE]))

        # Apply instructions
        for instruction in instructions:
            action = instruction.get(INSTRUCTION_ACTION)
            symbol = instruction.get(INSTRUCTION_SYMBOL)
            amount = instruction.get(
                INSTRUCTION_AMOUNT, instruction.get(INSTRUCTION_WEIGHT, 0)
            )

            if action == ACTION_REDUCE_EXPOSURE and symbol:
                if symbol in current_distribution:
                    current_distribution[symbol] = max(
                        0, current_distribution[symbol] - amount
                    )
            elif action == ACTION_INCREASE_EXPOSURE and symbol:
                if symbol in current_distribution:
                    current_distribution[symbol] += amount
                else:
                    current_distribution[symbol] = amount
            elif action == ACTION_ADD_TO_DISTRIBUTION and symbol:
                current_distribution[symbol] = amount
            elif action == ACTION_REMOVE_FROM_DISTRIBUTION and symbol:
                current_distribution.pop(symbol, None)
            elif action == ACTION_UPDATE_RATIO and symbol:
                current_distribution[symbol] = amount
            elif action == ACTION_INCREASE_FIAT_RATIO:
                # Assume USD or ref market
                ref_market = trading_mode.exchange_manager.exchange_personal_data.portfolio_manager.reference_market
                if ref_market in current_distribution:
                    current_distribution[ref_market] += amount
                else:
                    current_distribution[ref_market] = amount
            elif action == ACTION_DECREASE_FIAT_RATIO:
                ref_market = trading_mode.exchange_manager.exchange_personal_data.portfolio_manager.reference_market
                if ref_market in current_distribution:
                    current_distribution[ref_market] = max(
                        0, current_distribution[ref_market] - amount
                    )

        # Normalize to 100%
        total = sum(current_distribution.values())
        if total > 0:
            for asset in current_distribution:
                current_distribution[asset] = (
                    current_distribution[asset] / total
                ) * 100

        # Update trading_mode.ratio_per_asset
        trading_mode.ratio_per_asset = {
            asset: {
                index_distribution.DISTRIBUTION_NAME: asset,
                index_distribution.DISTRIBUTION_VALUE: weight,
            }
            for asset, weight in current_distribution.items()
        }
        trading_mode.total_ratio_per_asset = decimal.Decimal(100)

        # Update indexed_coins
        trading_mode.indexed_coins = list(current_distribution.keys())

    except Exception as e:
        trading_mode.logger.exception(f"Error applying AI instructions: {e}")
