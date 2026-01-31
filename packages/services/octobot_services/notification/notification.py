#  Drakkar-Software OctoBot-Services
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
import octobot_commons.enums as common_enums

import octobot_services.enums as enums


class Notification:
    def __init__(self, text: str, title: str, markdown_text: str, sound: enums.NotificationSound,
                 markdown_format: common_enums.MarkdownFormat,
                 level: enums.NotificationLevel, category: enums.NotificationCategory,
                 linked_notification):
        self.text = text
        self.markdown_text = markdown_text
        self.title = title
        self.level = level
        self.markdown_format = markdown_format
        self.linked_notification = linked_notification
        self.category = category
        self.sound = sound

        # Used to identify previous notification related elements when necessary ex: a tweet to reply to
        self.metadata = {}

    def __repr__(self):
        return f"[Notification] title: {self.title}, text: {self.text}, level: {self.level}, " \
               f"markdown_format: {self.markdown_format.name}, category: {self.category.value}, " \
               f"linked_notification: {self.linked_notification}"
