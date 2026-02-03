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
import octobot_services.notification as services_notification
import octobot_services.notifier as notifier
import tentacles.Services.Interfaces.web_interface as web_interface
import tentacles.Services.Services_bases as Services_bases


class WebNotifier(notifier.AbstractNotifier):
    REQUIRED_SERVICES = [Services_bases.WebService]
    NOTIFICATION_TYPE_KEY = "web"

    async def _handle_notification(self, notification: services_notification.Notification):
        await web_interface.add_notification(notification.level, notification.title,
                                             notification.text.replace("\n", "<br>"),
                                             sound=notification.sound.value)
