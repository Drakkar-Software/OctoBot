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
import octobot.constants as constants
import octobot.community.identifiers_provider as identifiers_provider
import octobot_commons.dataclasses as commons_dataclasses
import octobot_commons.enums as commons_enums


@dataclasses.dataclass
class CategoryData(commons_dataclasses.FlexibleDataclass):
    slug: str = ""
    name_translations: dict = dataclasses.field(default_factory=dict)
    type: str = ""
    metadata: dict = dataclasses.field(default_factory=dict)

    def get_url(self) -> str:
        if self.metadata:
            external_links = self.metadata.get("external_link")
            if external_links:
                if blog_slug := external_links.get("blog"):
                    return f"{identifiers_provider.IdentifiersProvider.COMMUNITY_LANDING_URL}/en/blog/{blog_slug}"
        return ""


@dataclasses.dataclass
class ResultsData(commons_dataclasses.FlexibleDataclass):
    profitability: dict = dataclasses.field(default_factory=dict)
    reference_market_profitability: dict = dataclasses.field(default_factory=dict)

    def _get_max(self):
        if not self.reference_market_profitability:
            return 0, "1m"
        max_unit = next(iter(self.reference_market_profitability))
        max_value = self.reference_market_profitability[max_unit]
        for unit, value in self.reference_market_profitability.items():
            if value > max_value:
                max_unit = unit
                max_value = value
        return max_value, max_unit

    def get_max_value(self):
        return self._get_max()[0]

    def get_max_unit(self):
        return self._get_max()[1]


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

    def get_name(self, locale, default_locale=constants.DEFAULT_LOCALE):
        return self.content["name_translations"].get(locale, default_locale)

    def get_url(self) -> str:
        return f"{identifiers_provider.IdentifiersProvider.COMMUNITY_URL}/strategies/{self.slug}"

    def get_risk(self) -> commons_enums.ProfileRisk:
        risk = self.attributes['risk'].upper()
        try:
            # use [] to access by name
            # https://docs.python.org/3/howto/enum.html#programmatic-access-to-enumeration-members-and-their-attributes
            return commons_enums.ProfileRisk[risk]
        except KeyError:
            return commons_enums.ProfileRisk.MODERATE
