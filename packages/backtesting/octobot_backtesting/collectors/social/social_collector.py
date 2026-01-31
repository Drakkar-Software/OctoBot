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
import octobot_backtesting.collectors as collectors


class SocialDataCollector(collectors.DataCollector):
    # IMPORTER = SocialDataImporter

    def __init__(self, config, social_name):
        super().__init__(config)
        self.social_name = social_name
        self.set_file_path()

    async def initialize(self):
        self.create_database()

        # TODO initialize with service
