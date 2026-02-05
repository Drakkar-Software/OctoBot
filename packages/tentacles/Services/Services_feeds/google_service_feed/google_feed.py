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
import asyncio
import time
import aiohttp

import simplifiedpytrends.exceptions
import simplifiedpytrends.request

import octobot_services.channel as services_channel
import octobot_services.constants as services_constants
import octobot_services.service_feeds as service_feeds
import tentacles.Services.Services_bases as Services_bases


class GoogleServiceFeedChannel(services_channel.AbstractServiceFeedChannel):
    pass


class TrendTopic:
    def __init__(self, refresh_time, keywords, category=0, time_frame="today 5-y", geo="", grop=""):
        self.keywords = keywords
        self.sanitized_keywords = [
            keyword.replace(" ", "+")
            for keyword in keywords
        ]
        self.category = category
        self.time_frame = time_frame
        self.geo = geo
        self.grop = grop
        self.refresh_time = refresh_time
        self.next_refresh = time.time()

    def __str__(self):
        return f"{self.keywords} {self.time_frame}"


class GoogleServiceFeed(service_feeds.AbstractServiceFeed):
    FEED_CHANNEL = GoogleServiceFeedChannel
    REQUIRED_SERVICES = [Services_bases.GoogleService]

    def __init__(self, config, main_async_loop, bot_id, backtesting=None, importer=None):
        super().__init__(config, main_async_loop, bot_id, backtesting=backtesting, importer=importer)
        self.trends_req_builder = None
        self.trends_topics = []
        self.listener_task = None

    def _initialize(self):
        # if the url changes (google sometimes changes it), use the following line:
        # trends_req.GENERAL_URL = "https://trends.google.com/trends/explore"
        self.trends_req_builder = simplifiedpytrends.request.TrendReq(hl='en-US', tz=0)

    # merge new config into existing config
    def update_feed_config(self, config):
        self.trends_topics.extend(topic
                                  for topic in config[services_constants.CONFIG_TREND_TOPICS]
                                  if topic not in self.trends_topics)

    def _something_to_watch(self):
        return bool(self.trends_topics)

    def _get_sleep_time_before_next_wakeup(self):
        closest_wakeup = min(topic.next_refresh for topic in self.trends_topics)
        return max(0, closest_wakeup - time.time())

    async def _get_topic_trend(self, topic):
        self.logger.debug(f"Fetching trend on {topic.keywords} over {topic.time_frame}")
        await self.trends_req_builder.async_build_payload(kw_list=topic.sanitized_keywords,
                                                          cat=topic.category,
                                                          timeframe=topic.time_frame,
                                                          geo=topic.geo,
                                                          gprop=topic.grop)
        topic.next_refresh = time.time() + topic.refresh_time
        return await self.trends_req_builder.async_interest_over_time()

    async def _push_update_and_wait(self):
        for topic in self.trends_topics:
            if time.time() >= topic.next_refresh:
                interest_over_time = await self._get_topic_trend(topic)
                if interest_over_time:
                    await self._async_notify_consumers(
                        {
                            services_constants.FEED_METADATA: f"{topic};{interest_over_time}",
                            services_constants.CONFIG_TREND: interest_over_time,
                            services_constants.CONFIG_TREND_DESCRIPTION: topic
                        }
                    )
        await asyncio.sleep(self._get_sleep_time_before_next_wakeup())

    async def _update_loop(self):
        async with aiohttp.ClientSession() as session:
            self.trends_req_builder.aiohttp_session = session
            while not self.should_stop:
                try:
                    await self._push_update_and_wait()
                except simplifiedpytrends.exceptions.ResponseError as e:
                    self.logger.exception(e, True, f"Error when fetching Google trends feed: {e} "
                                                   f"(response text: {await e.response.text()})")
                    self.should_stop = True
                except Exception as e:
                    self.logger.exception(e, True, f"Error when receiving Google feed: ({e})")
                    self.should_stop = True
            return False

    async def _start_service_feed(self):
        try:
            self.listener_task = asyncio.create_task(self._update_loop())
            return True
        except Exception as e:
            self.logger.exception(e, True, f"Error when initializing Google trends feed: {e}")
            return False

    async def stop(self):
        await super().stop()
        if self.listener_task is not None:
            self.listener_task.cancel()
            self.listener_task = None

