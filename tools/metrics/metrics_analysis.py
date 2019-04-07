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

import requests
import json

from tools.logging.logging_util import get_logger
from config import METRICS_URL
from tools.config_manager import ConfigManager


LOGGER = get_logger("MetricsAnalysis")


def get_community_metrics():
    if can_read_metrics:
        try:
            resp = requests.get(METRICS_URL)
            if resp.status_code != 200:
                LOGGER.error(f"Error when getting metrics: error code={resp.status_code}")
            else:
                return _format_metrics(json.loads(resp.text))
        except Exception as e:
            LOGGER.error(f"Error when getting metrics: {e}")
    else:
        return None


def can_read_metrics(config):
    return ConfigManager.get_metrics_enabled(config)


def _format_metrics(json_metrics):
    formatted_metrics = dict()
    formatted_metrics["total_count"] = len(json_metrics)

    return formatted_metrics
