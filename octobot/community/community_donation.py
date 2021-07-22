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


class CommunityDonation:
    def __init__(self, amount: str, currency: str, blockchain: str, transaction_id: str, address_to: str):
        self.amount = amount
        self.currency = currency
        self.blockchain = blockchain
        self.transaction_id = transaction_id
        self.address_to = address_to

    def __str__(self):
        return f"{self.amount} {self.currency} on {self.blockchain} ({self.transaction_id})"

    @staticmethod
    def from_community_dict(data):
        data_attributes = data.get("attributes", {})
        return CommunityDonation(
            data_attributes.get("amount"),
            data_attributes.get("currency"),
            data_attributes.get("blockchain"),
            data_attributes.get("transaction_id"),
            data_attributes.get("address_to")
        )
