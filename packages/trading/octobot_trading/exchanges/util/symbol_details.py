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
class CCXTDetails(octobot_commons.dataclasses.FlexibleDataclass, octobot_commons.dataclasses.UpdatableDataclass):
    info: dict = dataclasses.field(default_factory=dict)    # deprecated, will be removed soon
    parsed: dict = dataclasses.field(default_factory=dict)  # deprecated, will be removed soon


@dataclasses.dataclass
class SymbolDetails(octobot_commons.dataclasses.FlexibleDataclass, octobot_commons.dataclasses.UpdatableDataclass):
    ccxt: CCXTDetails = dataclasses.field(default_factory=CCXTDetails)
