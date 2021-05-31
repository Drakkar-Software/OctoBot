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
import asyncio
import aiohttp
import requests
import enum
from datetime import datetime, timedelta

import octobot_commons.logging as logging
import octobot_commons.constants as constants

import octobot.community.community_fields as community_fields


async def get_current_octobots_stats():
    logger = logging.get_logger("CommunityAnalysis")
    bots_stats = {}
    bot_metrics_url = f"{constants.METRICS_URL}metrics/community/count/"

    async def get_stats(url, stats_key):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        logger.error(f"Error when getting community status : error code={resp.status}")
                    else:
                        bots_stats[stats_key] = (await resp.json())["total"]
        except Exception as e:
            logger.exception(e, True, f"Error when getting community status : {e}")

    await asyncio.gather(
        get_stats(f"{bot_metrics_url}0/0/-1", "daily"),
        get_stats(f"{bot_metrics_url}0/-1/0", "monthly"),
        get_stats(f"{bot_metrics_url}0/0/0", "all")
    )
    # ugly workaround to prevent some of these current aiohttp version warnings:
    # "unclosed transport {'_pending_data': None, '_paused': False, '_sock': <socket.socket fd=-1,
    # family=AddressFamily.AF_INET, type=SocketKind.SOCK_STREAM, proto=6>,"
    await asyncio.sleep(0.01)
    return bots_stats


def get_community_metrics():
    logger = logging.get_logger("CommunityAnalysis")
    try:
        resp = requests.get(f"{constants.METRICS_URL}{constants.METRICS_ROUTE_COMMUNITY}")
        if resp.status_code != 200:
            logger.error(f"Error when getting community data : error code={resp.status_code}")
        else:
            return _format_community_data(resp.json())
    except Exception as e:
        logger.error(f"Error when getting metrics: {e}")


def can_read_metrics(config):
    return config.get_metrics_enabled()


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


def _get_min_timestamp(days):
    return (datetime.now() - timedelta(days=days)).timestamp()


def _is_started_after(item, min_time):
    return community_fields.CommunityFields.CURRENT_SESSION.value in item and \
           item[community_fields.CommunityFields.CURRENT_SESSION.value].get(
               community_fields.CommunityFields.UP_TIME.value, 0) >= min_time


def _get_count_last_months(json_bot_metrics, months):
    month_count = 0
    month_min_timestamp = _get_min_timestamp(months * 30.5)
    for item in json_bot_metrics:
        if _is_started_after(item, month_min_timestamp):
            month_count += 1
    return month_count


def _get_top_traded_item(json_bot_metrics, session_key, key, top_count=constants.COMMUNITY_TOPS_COUNT):
    last_month_min_timestamp = _get_min_timestamp(30.5)
    all_item_by_occurrence = _count_occurrences(json_bot_metrics, session_key, key, TraderTypes.ALL)
    monthly_real_item_by_occurrence = _count_occurrences(json_bot_metrics, session_key, key,
                                                         TraderTypes.REAL, last_month_min_timestamp)
    monthly_simulated_item_by_occurrence = _count_occurrences(json_bot_metrics, session_key, key,
                                                              TraderTypes.SIMULATED, last_month_min_timestamp)
    return {
        "all": _get_top_occurrences(all_item_by_occurrence, top_count),
        "monthly_real_traders": _get_top_occurrences(monthly_real_item_by_occurrence, top_count),
        "monthly_simulated_traders": _get_top_occurrences(monthly_simulated_item_by_occurrence, top_count)
    }


def _get_top_occurrences(item_by_occurrence, top_count):
    items = [{"name": key, "count": val} for key, val in item_by_occurrence.items()]
    sorted_items = sorted(items, key=lambda x: x["count"], reverse=True)[:top_count]
    for i, item in enumerate(sorted_items):
        item["rank"] = i + 1
    return sorted_items


def _count_occurrences(items, session_key, key, trader_type, since=0.0):
    occurrences_by_item = {}
    for item in items:
        if _is_started_after(item, since) and _is_of_trader_type(item, trader_type):
            if session_key in item and key in item[session_key]:
                for pair in item[session_key][key]:
                    if pair in occurrences_by_item:
                        occurrences_by_item[pair] += 1
                    else:
                        occurrences_by_item[pair] = 1
    return occurrences_by_item


def _is_of_trader_type(item, trader_type):
    if trader_type is TraderTypes.ALL:
        return True
    else:
        session = item.get(community_fields.CommunityFields.CURRENT_SESSION.value, {})
        if trader_type is TraderTypes.REAL \
                and session.get(community_fields.CommunityFields.TRADER.value, False):
            return True
        elif trader_type is TraderTypes.SIMULATED \
                and not session.get(community_fields.CommunityFields.TRADER.value, False) \
                and session.get(community_fields.CommunityFields.SIMULATOR.value, False):
            return True
        return False


class TraderTypes(enum.Enum):
    ALL = "all"
    REAL = "real"
    SIMULATED = "simulated"
