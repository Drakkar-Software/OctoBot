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
import dataclasses
import decimal
import typing

import octobot_trading.errors
import octobot_trading.personal_data.orders.trailing_profiles.trailing_profile_types as trailing_profile_types
import octobot_trading.personal_data.orders.trailing_profiles.trailing_profile as trailing_profile
import octobot_trading.personal_data.orders.trailing_profiles.trailing_price_step as trailing_price_step


@dataclasses.dataclass
class FilledTakeProfitTrailingProfile(trailing_profile.TrailingProfile):
    """
    To be used alongside TrailingOnFilledTPBalancedOrderGroup
    """
    steps: list[trailing_price_step.TrailingPriceStep]

    # pylint: disable=E1134
    def __post_init__(self):
        if self.steps and isinstance(self.steps[0], dict):
            self.steps = [
                trailing_price_step.TrailingPriceStep.from_dict(step)
                for step in self.steps
            ]

    @staticmethod
    def get_type() -> trailing_profile_types.TrailingProfileTypes:
        return trailing_profile_types.TrailingProfileTypes.FILLED_TAKE_PROFIT

    def update_and_get_trailing_price(self, updated_price: decimal.Decimal) -> typing.Optional[decimal.Decimal]:
        if updated_step := self._get_updated_step(updated_price):
            updated_step.reached = True
            return decimal.Decimal(str(updated_step.trailing_price))
        return None

    def _reach_outdated_steps_and_check_price(self, updated_price: decimal.Decimal) -> bool:
        ordered_steps = self._get_ordered_remaining_steps()
        first_newly_reached_step_index = None
        last_newly_reached_step_index = None
        float_price = float(updated_price)
        for index, step in enumerate(ordered_steps):
            if not step.reached and step.should_be_reached(float_price):
                if first_newly_reached_step_index is None:
                    first_newly_reached_step_index = index
                last_newly_reached_step_index = index
        if first_newly_reached_step_index is None:
            # price not reached
            return False
        if last_newly_reached_step_index > first_newly_reached_step_index:
            for step in ordered_steps[first_newly_reached_step_index:last_newly_reached_step_index]:
                # step has been reached already and should be skipped
                step.reached = True
        return True

    def _get_ordered_remaining_steps(self) -> list[trailing_price_step.TrailingPriceStep]:
        return [
            step
            for step in sorted(self.steps, key=lambda x: x.step_price * (1 if x.trigger_above else -1))
            if not step.reached
        ]

    def _get_updated_step(self, updated_price: decimal.Decimal) -> typing.Optional[trailing_price_step.TrailingPriceStep]:
        if self._reach_outdated_steps_and_check_price(updated_price):
            try:
                return self._get_ordered_remaining_steps()[0]
            except IndexError:
                raise octobot_trading.errors.ExhaustedTrailingProfileError(
                    f"All {len(self.steps)} trailing steps have been reached"
                )
        return None

