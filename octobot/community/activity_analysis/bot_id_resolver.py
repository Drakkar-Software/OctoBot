#  This file is part of OctoBot (https://github.com/Drakkar-Software/OctoBot)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
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
import dataclasses
import uuid

import octobot_commons.configuration as configuration
import octobot_commons.constants as commons_constants


@dataclasses.dataclass(frozen=True)
class BotIdResolution:
    bot_id: str
    was_created: bool


def _get_metrics_section(config: configuration.Configuration) -> dict:
    metrics_section = config.config.setdefault(commons_constants.CONFIG_METRICS, {})
    if not isinstance(metrics_section, dict):
        raise ValueError(f"{commons_constants.CONFIG_METRICS} must be a mapping in config")
    return metrics_section


def ensure_activity_bot_id(config: configuration.Configuration) -> BotIdResolution:
    metrics_section = _get_metrics_section(config)
    stored_bot_id = metrics_section.get(commons_constants.CONFIG_METRICS_ACTIVITY_BOT_ID)
    if stored_bot_id:
        return BotIdResolution(
            bot_id=str(stored_bot_id),
            was_created=False,
        )
    new_bot_id = str(uuid.uuid4())
    metrics_section[commons_constants.CONFIG_METRICS_ACTIVITY_BOT_ID] = new_bot_id
    config.save()
    return BotIdResolution(
        bot_id=new_bot_id,
        was_created=True,
    )
