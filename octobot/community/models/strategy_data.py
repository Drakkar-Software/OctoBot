#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
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
import octobot_commons.profiles as profiles

CATEGORY_NAME_TRANSLATIONS_BY_SLUG = {
    "coingecko-index": {"en": "Crypto Basket"}
}
DEFAULT_LOGO_NAME_BY_SLUG = {
    "coingecko-index": "crypto-basket.png",
}
AUTO_UPDATED_CATEGORIES = ["coingecko-index"]
DEFAULT_LOGO_NAME = "default_strategy.png"
EXTENSION_CATEGORIES = ["coingecko-index"]

CUSTOM_STRATEGY_PREFIX = "[Custom]_"
CUSTOM_CATEGORY_SLUG_PREFIX = "creator-"


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
                    return f"{identifiers_provider.IdentifiersProvider.COMMUNITY_URL}/en/blog/{blog_slug}"
                if features_slug := external_links.get("features"):
                    return f"{identifiers_provider.IdentifiersProvider.COMMUNITY_URL}/features/{features_slug}"
        return ""

    def get_default_logo_url(self) -> str:
        return DEFAULT_LOGO_NAME_BY_SLUG.get(self.slug, DEFAULT_LOGO_NAME)

    def get_name(self, locale, default_locale=constants.DEFAULT_LOCALE):
        return CATEGORY_NAME_TRANSLATIONS_BY_SLUG.get(self.slug, self.name_translations).get(locale, default_locale)

    def is_auto_updated(self) -> bool:
        return self.slug in AUTO_UPDATED_CATEGORIES

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
            if value is None:
                continue
            if max_value is None:
                max_value = value
            if value > max_value:
                max_unit = unit
                max_value = value
        if max_value is None:
            max_value = 0
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

    def get_product_url(self) -> str:
        return f"{identifiers_provider.IdentifiersProvider.COMMUNITY_URL}/strategies/{self.slug}"

    def get_risk(self) -> commons_enums.ProfileRisk:
        try:
            risk = self.attributes['risk'].upper()
            # use [] to access by name
            # https://docs.python.org/3/howto/enum.html#programmatic-access-to-enumeration-members-and-their-attributes
            return commons_enums.ProfileRisk[risk]
        except KeyError:
            return commons_enums.ProfileRisk.MODERATE

    def get_logo_url(self, prefix: str) -> str:
        if self.logo_url:
            return self.logo_url
        return f"{prefix}{self.category.get_default_logo_url()}"

    def is_auto_updated(self) -> bool:
        return self.category.is_auto_updated()

    def is_extension_only(self) -> bool:
        return self.category.slug in EXTENSION_CATEGORIES


def is_custom_category(category: dict) -> bool:
    if slug := category.get('slug'):
        return slug.startswith(CUSTOM_CATEGORY_SLUG_PREFIX)
    return False


def get_custom_strategy_name(base_name) -> str:
    return f"{CUSTOM_STRATEGY_PREFIX}{base_name}"


def is_custom_strategy_profile(profile: profiles.ProfileData) -> bool:
    return (
        profile.profile_details.name
        and profile.profile_details.name.startswith(CUSTOM_STRATEGY_PREFIX)
    )
