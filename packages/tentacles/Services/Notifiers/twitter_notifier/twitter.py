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
import octobot_services.notification as notification
import octobot_services.notifier as notifier
import tentacles.Services.Services_bases as Services_bases


# disable inheritance to disable tentacle visibility. Disabled as starting from feb 9 2023, API is now paid only
# class TwitterNotifier(notifier.AbstractNotifier):
class TwitterNotifier:
    REQUIRED_SERVICES = [Services_bases.TwitterService]
    NOTIFICATION_TYPE_KEY = "twitter"

    async def _handle_notification(self, notification: notification.Notification):
        self.logger.debug(f"sending notification: {notification}")
        if notification.linked_notification is None:
            result = await self._send_regular_tweet(notification)
        else:
            result = await self._send_tweet_reply(notification)
        if result is None:
            self.logger.error(f"Tweet is not sent, notification: {notification}")
        else:
            self.logger.info("Tweet sent")

    async def _send_regular_tweet(self, notification):
        result = await self.services[0].post(self._get_tweet_text(notification), True)
        notification.metadata[self.NOTIFICATION_TYPE_KEY] = result
        return result

    async def _send_tweet_reply(self, notification):
        try:
            previous_tweet_id = notification.linked_notification.metadata[self.NOTIFICATION_TYPE_KEY].id
            result = await self.services[0].respond(previous_tweet_id, self._get_tweet_text(notification), True)
            notification.metadata[self.NOTIFICATION_TYPE_KEY] = result
            return result
        except (KeyError, AttributeError):
            return await self._send_regular_tweet(notification)

    @staticmethod
    def _get_tweet_text(notification):
        return f"{notification.title}\n{notification.text}" if notification.title else notification.text
