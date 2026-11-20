#  Drakkar-Software OctoBot-Tentacles
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
import datetime
import dataclasses

import octobot_services.constants as services_constants
import octobot_services.services as services

import tentacles.Services.Services_bases.coindesk_service.models as coindesk_models


class CoindeskService(services.AbstractService):    
    API_RATE_LIMIT_SECONDS = 10
    
    @staticmethod
    def is_setup_correctly(config):
        return True

    @staticmethod
    def get_is_enabled(config):
        return True

    def has_required_configuration(self):
        return True

    def get_endpoint(self) -> None:
        return None

    def get_type(self) -> None:
        return services_constants.CONFIG_COINDESK

    async def prepare(self) -> None:
        pass

    def get_successful_startup_message(self):
        return "", True

    def _datetime_to_ms_timestamp(self, dt):
        """Convert datetime to milliseconds timestamp"""
        # Handle datetime object (most common case)
        if isinstance(dt, datetime.datetime):
            # Convert to UTC if timezone-naive
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=datetime.timezone.utc)
            return int(dt.timestamp() * 1000)
        
        # Handle Unix timestamp (seconds or milliseconds)
        if isinstance(dt, (int, float)):
            return int(dt * 1000) if dt < 1e10 else int(dt)
        
        # Handle datetime string (fallback)
        if isinstance(dt, str):
            try:
                # Try ISO format
                dt_obj = datetime.datetime.fromisoformat(dt.replace('Z', '+00:00'))
                if dt_obj.tzinfo is None:
                    dt_obj = dt_obj.replace(tzinfo=datetime.timezone.utc)
                return int(dt_obj.timestamp() * 1000)
            except ValueError:
                self.logger.warning(f"Could not parse datetime: {dt}")
                return None
        
        return None

    def _convert_news_to_event(self, news_item: coindesk_models.CoindeskNews, source: str) -> dict:
        """Convert CoindeskNews dataclass to event dict"""
        timestamp_ms = self._datetime_to_ms_timestamp(news_item.published_on)
        if timestamp_ms is None:
            return None
        
        return {
            "timestamp": timestamp_ms,
            "payload": dataclasses.asdict(news_item),
            "channel": source or services_constants.COINDESK_TOPIC_NEWS,
            "symbol": ""
        }

    def _convert_marketcap_to_event(self, marketcap_item: coindesk_models.CoindeskMarketcap, source: str) -> dict:
        """Convert CoindeskMarketcap dataclass to event dict"""
        timestamp_ms = self._datetime_to_ms_timestamp(marketcap_item.timestamp)
        if timestamp_ms is None:
            return None
        
        return {
            "timestamp": timestamp_ms,
            "payload": dataclasses.asdict(marketcap_item),
            "channel": source or services_constants.COINDESK_TOPIC_MARKETCAP,
            "symbol": ""
        }
