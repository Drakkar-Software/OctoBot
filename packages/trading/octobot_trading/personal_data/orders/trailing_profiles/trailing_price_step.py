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

import octobot_commons.dataclasses

@dataclasses.dataclass
class TrailingPriceStep(octobot_commons.dataclasses.FlexibleDataclass):
    trailing_price: float
    step_price: float
    trigger_above: bool
    reached: bool = False

    def should_be_reached(self, updated_price: float) -> bool:
        if self.trigger_above:
            return updated_price >= self.step_price
        return updated_price <= self.step_price