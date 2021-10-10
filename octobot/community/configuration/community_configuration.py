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


class CommunityConfiguration:
    def __init__(self,
                 identifier: str = None,
                 name: str = None,
                 config_archive: str = None,
                 created_at: str = None,
                 updated_at: str = None):
        self.identifier: str = identifier
        self.name: str = name
        self.config_archive: str = config_archive
        self.created_at: str = created_at
        self.updated_at: str = updated_at

    def to_dict(self, with_archive=True):
        data = {"name": self.name}
        if with_archive:
            # TODO
            data["config_archive"] = self.config_archive
        return data

    def __str__(self):
        return f"{self.name}, created_at: {self.created_at}, updated_at: {self.updated_at} " \
               f"(id:{self.identifier}, config_archive: {self.config_archive})"

    @staticmethod
    def from_community_dict(data):
        data_attributes = data.get("attributes", {})
        return CommunityConfiguration(
            data_attributes.get("id"),
            data_attributes.get("name"),
            None,
            data_attributes.get("created_at"),
            data_attributes.get("updated_at"),
        )
