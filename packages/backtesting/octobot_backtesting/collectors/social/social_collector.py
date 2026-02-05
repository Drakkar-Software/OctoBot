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
import json
import logging
import abc
import time

import octobot_backtesting.collectors.data_collector as data_collector
import octobot_backtesting.constants as constants
import octobot_backtesting.enums as enums
import octobot_backtesting.importers as importers

try:
    import octobot_services.constants as services_constants
except ImportError:
    logging.error("SocialDataCollector requires OctoBot-Services package installed")


class SocialDataCollector(data_collector.DataCollector):
    VERSION = constants.CURRENT_VERSION
    IMPORTER = importers.SocialDataImporter

    def __init__(self, config, services, tentacles_setup_config=None, sources=None, symbols=None,
                 use_all_available_sources=False,
                 data_format=enums.DataFormats.REGULAR_COLLECTOR_DATA,
                 start_timestamp=None, end_timestamp=None):
        super().__init__(config, data_format=data_format)
        self.tentacles_setup_config = tentacles_setup_config
        self.sources = sources if sources else []
        self.symbols = symbols if symbols else []
        self.use_all_available_sources = use_all_available_sources
        self.start_timestamp = start_timestamp
        self.end_timestamp = end_timestamp
        self.services = services if services else []
        self.primary_service = self.services[0] if self.services else ""
        self.current_step_index = 0
        self.total_steps = 0
        self.current_step_percent = 0
        self.set_file_path()

    def get_current_step_index(self):
        return self.current_step_index

    def get_total_steps(self):
        return self.total_steps

    def get_current_step_percent(self):
        return self.current_step_percent

    @abc.abstractmethod
    def _load_all_available_sources(self):
        raise NotImplementedError("_load_all_available_sources is not implemented")

    async def initialize(self):
        self.create_database()
        await self.database.initialize()

        # set config from params
        if self.sources:
            self.config.setdefault("sources", self.sources)
        # get service config if available
        if self.primary_service:
            existing_service_config = self.config.get(
                services_constants.CONFIG_CATEGORY_SERVICES, {}
            ).get(self.primary_service, {})
            self.config[services_constants.CONFIG_CATEGORY_SERVICES] = {
                self.primary_service: existing_service_config
            }
        if self.symbols:
            self.config.setdefault("symbols", [str(symbol) for symbol in self.symbols])

    def _load_sources_if_necessary(self):
        if self.use_all_available_sources:
            self._load_all_available_sources()
        if self.sources:
            self.config["sources"] = self.sources

    async def _create_description(self):
        timestamp = time.time()
        description = {
            "version": self.VERSION,
            "type": enums.DataType.SOCIAL.value,
            "sources": json.dumps(self.sources) if self.sources else json.dumps([]),
            "symbols": json.dumps([str(symbol) for symbol in self.symbols]) if self.symbols else json.dumps([]),
            "start_timestamp": int(self.start_timestamp / 1000) if self.start_timestamp else 0,
            "end_timestamp": int(self.end_timestamp / 1000) if self.end_timestamp
            else int(time.time()) if self.start_timestamp else 0,
        }
        description["services"] = json.dumps(self.services or [])
        await self.database.insert(enums.DataTables.DESCRIPTION, timestamp, **description)

    async def save_event(self, timestamp, service_name, channel=None, symbol=None, payload=None, multiple=False):
        if not multiple:
            await self.database.insert(enums.SocialDataTables.SOCIAL_EVENTS, timestamp,
                                       service_name=service_name,
                                       channel=channel if channel else "",
                                       symbol=symbol if symbol else "",
                                       payload=json.dumps(payload))
        else:
            # When multiple=True, timestamp should be a list, and varying fields should be lists
            # service_name stays constant, channel and symbol can be lists or single values
            channel_list = channel if isinstance(channel, list) else [channel if channel else "" for _ in payload]
            symbol_list = symbol if isinstance(symbol, list) else [symbol if symbol else "" for _ in payload]
            await self.database.insert_all(enums.SocialDataTables.SOCIAL_EVENTS, timestamp=timestamp,
                                           service_name=service_name,
                                           channel=channel_list,
                                           symbol=symbol_list,
                                           payload=[json.dumps(p) for p in payload])

    async def delete_all(self, table, service_name, channel=None, symbol=None):
        kwargs = {
            "service_name": service_name,
        }
        if channel:
            kwargs["channel"] = channel
        if symbol:
            kwargs["symbol"] = symbol
        await self.database.delete(table, **kwargs)
