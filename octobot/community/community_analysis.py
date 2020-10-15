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

import octobot_commons.logging as logging
import octobot_commons.constants as constants
import octobot_commons.config_manager as config_manager

import octobot.community.community_fields as community_fields

LOGGER = logging.get_logger("CommunityAnalysis")


def get_community_metrics():
    try:
        resp = requests.get(f"{constants.METRICS_URL}{constants.METRICS_ROUTE_COMMUNITY}")
        if resp.status_code != 200:
            LOGGER.error(f"Error when getting community data : error code={resp.status_code}")
        else:
            return _format_community_data(json.loads(resp.text))
    except Exception as e:
        LOGGER.error(f"Error when getting metrics: {e}")


def can_read_metrics(config):
    return config_manager.get_metrics_enabled(config)


def _format_community_data(json_bot_metrics):
    formatted_community_data = dict()
    formatted_community_data["total_count"] = len(json_bot_metrics)
    formatted_community_data["this_month"] = _get_count_last_months(json_bot_metrics, 1)
    formatted_community_data["last_six_month"] = _get_count_last_months(json_bot_metrics, 6)
    formatted_community_data["top_pairs"] = _get_top_traded_item(json_bot_metrics,
                                                                 community_fields.CommunityFields.CURRENT_SESSION.value,
                                                                 community_fields.CommunityFields.PAIRS.value)
    formatted_community_data["top_exchanges"] = _get_top_traded_item(json_bot_metrics,
                                                                     community_fields.CommunityFields.CURRENT_SESSION.value,
                                                                     community_fields.CommunityFields.EXCHANGES.value)
    formatted_community_data["top_strategies"] = _get_top_traded_item(json_bot_metrics,
                                                                      community_fields.CommunityFields.CURRENT_SESSION.value,
                                                                      community_fields.CommunityFields.EVAL_CONFIG.value)
    return formatted_community_data


def _get_count_last_months(json_bot_metrics, months):
    month_count = 0
    month_min_timestamp = (datetime.now() - timedelta(days=months * 30.5)).timestamp()
    for item in json_bot_metrics:
        if community_fields.CommunityFields.CURRENT_SESSION.value in item and \
                community_fields.CommunityFields.UP_TIME.value in item[community_fields.CommunityFields.CURRENT_SESSION.value] and \
                item[community_fields.CommunityFields.CURRENT_SESSION.value][
                    community_fields.CommunityFields.UP_TIME.value] >= month_min_timestamp:
            month_count += 1
    return month_count


def _get_top_traded_item(json_bot_metrics, session_key, key, top_count=constants.COMMUNITY_TOPS_COUNT):
    pair_by_occurrence = _count_occurrences(json_bot_metrics, session_key, key)
    return _get_top_occurrences(pair_by_occurrence, top_count)


def _get_top_occurrences(item_by_occurrence, top_count):
    items = [{"name": key, "count": val} for key, val in item_by_occurrence.items()]
    sorted_items = sorted(items, key=lambda x: x["count"], reverse=True)[:top_count]
    for i, item in enumerate(sorted_items):
        item["rank"] = i + 1
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
