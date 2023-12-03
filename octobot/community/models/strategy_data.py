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
import dataclasses
import octobot_commons.dataclasses as commons_dataclasses


@dataclasses.dataclass
class CategoryData(commons_dataclasses.FlexibleDataclass):
    slug: str = ""
    name_translations: dict = dataclasses.field(default_factory=dict)
    type: str = ""


@dataclasses.dataclass
class ResultsData(commons_dataclasses.FlexibleDataclass):
    profitability: dict = dataclasses.field(default_factory=dict)
    reference_market_profitability: dict = dataclasses.field(default_factory=dict)

    def get_max(self, key):
        return max(
            self.profitability.get(key, 0),
            self.reference_market_profitability.get(key, 0)
        )


@dataclasses.dataclass
class StrategyData(commons_dataclasses.FlexibleDataclass):
    id: str = ""
    slug: str = ""
    author_id: str = ""
    content: dict = dataclasses.field(default_factory=dict)
    category: CategoryData = dataclasses.field(default_factory=CategoryData.from_dict)
    results: ResultsData = dataclasses.field(default_factory=ResultsData.from_dict)
    logo_url: str = ""
    attributes: dict = dataclasses.field(default_factory=dict)
    visibility: str = ""
    metadata: str = ""
