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
from datetime import datetime, timedelta

from tools.logging.logging_util import get_logger
from config import METRICS_URL, MetricsFields, COMMUNITY_TOPS_COUNT, METRICS_ROUTE_COMMUNITY
from tools.config_manager import ConfigManager


LOGGER = get_logger("MetricsAnalysis")


def get_community_metrics():
    try:
        resp = requests.get(f"{METRICS_URL}{METRICS_ROUTE_COMMUNITY}")
        if resp.status_code != 200:
            LOGGER.error(f"Error when getting metrics: error code={resp.status_code}")
        else:
            return _format_metrics(json.loads(resp.text))
    except Exception as e:
        LOGGER.error(f"Error when getting metrics: {e}")


def can_read_metrics(config):
    return ConfigManager.get_metrics_enabled(config)


def _format_metrics(json_bot_metrics):
    formatted_metrics = dict()
    formatted_metrics["total_count"] = len(json_bot_metrics)
    formatted_metrics["this_month"] = _get_count_last_months(json_bot_metrics, 1)
    formatted_metrics["last_six_month"] = _get_count_last_months(json_bot_metrics, 6)
    formatted_metrics["top_pairs"] = _get_top_traded_item(json_bot_metrics, MetricsFields.CURRENT_SESSION.value,
                                                          MetricsFields.PAIRS.value)
    formatted_metrics["top_exchanges"] = _get_top_traded_item(json_bot_metrics, MetricsFields.CURRENT_SESSION.value,
                                                              MetricsFields.EXCHANGES.value)
    formatted_metrics["top_strategies"] = _get_top_traded_item(json_bot_metrics, MetricsFields.CURRENT_SESSION.value,
                                                               MetricsFields.EVAL_CONFIG.value)
    return formatted_metrics


def _get_count_last_months(json_bot_metrics, months):
    month_count = 0
    month_min_timestamp = (datetime.now() - timedelta(days=months*30.5)).timestamp()
    for item in json_bot_metrics:
        if MetricsFields.CURRENT_SESSION.value in item and \
                MetricsFields.UP_TIME.value in item[MetricsFields.CURRENT_SESSION.value] and \
                item[MetricsFields.CURRENT_SESSION.value][MetricsFields.UP_TIME.value] >= month_min_timestamp:
            month_count += 1
    return month_count


def _get_top_traded_item(json_bot_metrics, session_key, key, top_count=COMMUNITY_TOPS_COUNT):
    pair_by_occurrence = _count_occurrences(json_bot_metrics, session_key, key)
    return _get_top_occurrences(pair_by_occurrence, top_count)


def _get_top_occurrences(item_by_occurrence, top_count):
    items = [{"name": key, "count": val} for key, val in item_by_occurrence.items()]
    sorted_items = sorted(items, key=lambda x: x["count"], reverse=True)[:top_count]
    for i, item in enumerate(sorted_items):
        item["rank"] = i+1
    return sorted_items


def _count_occurrences(items, session_key, key):
    occurrences_by_item = {}
    for item in items:
        if session_key in item and key in item[session_key]:
            for pair in item[session_key][key]:
                if pair in occurrences_by_item:
                    occurrences_by_item[pair] += 1
                else:
                    occurrences_by_item[pair] = 1
    return occurrences_by_item
