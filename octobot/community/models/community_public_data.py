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
import octobot.community.supabase_backend.enums as enums


class CommunityPublicData:
    def __init__(self):
        self.products = _DataElement({}, False)

    def set_products(self, products):
        self.products.value = {product[enums.ProductKeys.ID.value]: product for product in products}
        self.products.fetched = True

    def get_product_slug(self, product_id):
        return self.products.value[product_id][enums.ProductKeys.SLUG.value]


@dataclasses.dataclass
class _DataElement:
    value: any
    fetched: bool
