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
import asyncio
import time
import aiohttp

import octobot_commons.logging as logging
import octobot_commons.constants as commons_constants
import octobot.constants as constants


async def get_current_octobots_stats():
    bot_metrics_url = f"{commons_constants.METRICS_URL}metrics/community/count/"
    return await _get_stats({
        "daily": f"{bot_metrics_url}0/0/-1",
        "monthly": f"{bot_metrics_url}0/-1/0",
        "all": f"{bot_metrics_url}0/0/0"
    })


async def _ensure_closed_sockets():
    # ugly workaround to prevent some of these current aiohttp version warnings:
    # "unclosed transport {'_pending_data': None, '_paused': False, '_sock': <socket.socket fd=-1,
    # family=AddressFamily.AF_INET, type=SocketKind.SOCK_STREAM, proto=6>,"
    await asyncio.sleep(0.01)


async def _get_stats(endpoint_by_key):
    logger = logging.get_logger("CommunityAnalysis")
    bots_stats = {}

    async def get_stats(url, stats_key):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        logger.error(f"Error when getting community status : error code={resp.status}")
                    else:
                        json_resp = await resp.json()
                        if "total" in json_resp:
                            bots_stats[stats_key] = json_resp["total"]
                        else:
                            bots_stats[stats_key] = _format_top_elements(json_resp)
        except Exception as e:
            logger.exception(e, True, f"Error when getting community status : {e}")
    await asyncio.gather(
        *(
            get_stats(endpoint, key)
            for key, endpoint in endpoint_by_key.items()
        )
    )
    await _ensure_closed_sockets()
    return bots_stats


async def get_community_metrics():
    bot_count_metrics_url = f"{commons_constants.METRICS_URL}metrics/community/count/"
    bot_top_metrics_url = f"{commons_constants.METRICS_URL}metrics/community/top/"
    one_month_time = int(time.time() - 30 * commons_constants.DAYS_TO_SECONDS)
    simulated = "?traderType=simulated"
    real = "?traderType=real"
    return await _get_stats({
        "this_month": f"{bot_count_metrics_url}0/-1/0",
        "last_six_month": f"{bot_count_metrics_url}0/-6/0",
        "total_count": f"{bot_count_metrics_url}0/0/0",
        "top_simulated_exchanges": f"{bot_top_metrics_url}exchanges/{one_month_time}{simulated}",
        "top_real_exchanges": f"{bot_top_metrics_url}exchanges/{one_month_time}{real}",
        "top_simulated_pairs": f"{bot_top_metrics_url}pairs/{one_month_time}{simulated}",
        "top_real_pairs": f"{bot_top_metrics_url}pairs/{one_month_time}{real}",
        "top_simulated_eval_config": f"{bot_top_metrics_url}evaluation_configs/{one_month_time}{simulated}",
        "top_real_eval_config": f"{bot_top_metrics_url}evaluation_configs/{one_month_time}{real}",
    })


def can_read_metrics(config):
    return constants.IS_CLOUD_ENV or config.get_metrics_enabled()


def _format_top_elements(top_elements):
    return [
        {
            "name": element["name"],
            "count": element["count"],
            "rank": index,
        }
        for index, element in enumerate(top_elements)
    ]
