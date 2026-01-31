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
import octobot_commons.enums as commons_enums
import octobot_services.notification as notification
import octobot_services.notifier as notifier
import tentacles.Services.Services_bases as Services_bases


class TelegramNotifier(notifier.AbstractNotifier):
    REQUIRED_SERVICES = [Services_bases.TelegramService]
    NOTIFICATION_TYPE_KEY = "telegram"
    USE_MAIN_LOOP = True

    async def _handle_notification(self, notification: notification.Notification):
        self.logger.debug(f"sending notification: {notification}")
        text, use_markdown = self._get_message_text(notification)
        await self._send_message(notification, text, use_markdown)

    async def _send_message(self, notification, text, use_markdown):
        try:
            previous_message_id = notification.linked_notification.metadata[self.NOTIFICATION_TYPE_KEY].message_id \
                if notification.linked_notification and \
                   self.NOTIFICATION_TYPE_KEY in notification.linked_notification.metadata else None
        except (KeyError, AttributeError):
            previous_message_id = None
        sent_message = await self.services[0].send_message(text,
                                                           markdown=use_markdown,
                                                           reply_to_message_id=previous_message_id)
        if sent_message is None and previous_message_id is not None:
            # failed to reply, try regular message
            self.logger.warning(f"Failed to reply to message with id {previous_message_id}, sending regular message.")
            sent_message = await self.services[0].send_message(text,
                                                               markdown=use_markdown,
                                                               reply_to_message_id=None)
        notification.metadata[self.NOTIFICATION_TYPE_KEY] = sent_message

    @staticmethod
    def _get_message_text(notification):
        title = notification.title
        text = notification.markdown_text if notification.markdown_text else notification.text
        if notification.markdown_format not in (commons_enums.MarkdownFormat.NONE, commons_enums.MarkdownFormat.IGNORE):
            text = f"{notification.markdown_format.value}{text}{notification.markdown_format.value}"
        if title:
            title = f"{commons_enums.MarkdownFormat.CODE.value}{title}{commons_enums.MarkdownFormat.CODE.value}"
            text = f"{title}\n{text}"
        use_markdown = notification.markdown_format is not commons_enums.MarkdownFormat.NONE
        return text, use_markdown
