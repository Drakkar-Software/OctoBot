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
import asyncio
import os
import time
import typing
import uuid

import aiofiles
import octobot_commons.json_util as json_util
import octobot_commons.logging as logging
import octobot_trading.api as trading_api

import octobot.constants as octobot_app_constants
import octobot_flow.entities.accounts.exchange_account_elements as exchange_account_elements_import
import octobot_flow.entities.accounts.process_bot_state as process_bot_state_import


if typing.TYPE_CHECKING:
    import octobot.octobot


def _synced_exchange_account_elements_for_first_trading_exchange(
    octobot: "octobot.octobot.OctoBot",
) -> exchange_account_elements_import.ExchangeAccountElements:
    """
    Build one snapshot for the first trading exchange only. If several are trading, log an error
    for each additional one (only the first is included in the dump).
    """
    empty = exchange_account_elements_import.ExchangeAccountElements()
    if octobot is None or octobot.exchange_producer is None:
        return empty
    managers = [
        trading_api.get_exchange_manager_from_exchange_id(exchange_manager_id)
        for exchange_manager_id in octobot.exchange_producer.exchange_manager_ids
    ]
    trading_managers = trading_api.get_trading_exchanges(managers)
    if not trading_managers:
        return empty
    first_exchange_manager = trading_managers[0]
    elements = exchange_account_elements_import.ExchangeAccountElements()
    elements.name = trading_api.get_exchange_name(first_exchange_manager)
    elements.sync_from_exchange_manager(first_exchange_manager, [])
    for skipped_exchange_manager in trading_managers[1:]:
        _get_logger().error(
            "process bot state dump includes only the first trading exchange; dumping %s (%s). "
            "Skipping additional trading exchange %s (%s).",
            trading_api.get_exchange_name(first_exchange_manager),
            trading_api.get_exchange_manager_id(first_exchange_manager),
            trading_api.get_exchange_name(skipped_exchange_manager),
            trading_api.get_exchange_manager_id(skipped_exchange_manager),
        )
    return elements


async def _write_state_file_async(
    state_file_path: str,
    interval: float,
    bot: "octobot.octobot.OctoBot",
) -> None:
    now = time.time()
    state = process_bot_state_import.ProcessBotState(
        metadata=process_bot_state_import.Metadata(
            updated_at=now,
            next_updated_at=now + interval,
            pid=os.getpid(),
        ),
        exchange_account_elements=_synced_exchange_account_elements_for_first_trading_exchange(
            bot,
        ),
    )
    content = state.to_dict(include_default_values=False)
    str_content = json_util.dump_formatted_json(content)
    full_path = os.path.abspath(state_file_path)
    directory = os.path.dirname(full_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    tmp_name = f"{full_path}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    try:
        async with aiofiles.open(tmp_name, mode="w", encoding="utf-8") as write_file:
            await write_file.write(str_content)
        os.replace(tmp_name, full_path)
    except Exception:
        if os.path.isfile(tmp_name):
            try:
                os.remove(tmp_name)
            except OSError:
                pass
        raise


async def run_periodic_dump_loop(state_file_path: str, bot: "octobot.octobot.OctoBot") -> None:
    """
    Periodically write ProcessBotState next to the user config. Cancel the task to stop.
    """
    interval = octobot_app_constants.PROCESS_BOT_STATE_DUMP_INTERVAL_SECONDS
    while True:
        try:
            await _write_state_file_async(state_file_path, interval, bot)
        except asyncio.CancelledError:
            raise
        except Exception as err:  # pylint: disable=broad-except
            _get_logger().exception(err, True, "process bot state dump failed: %s", err)
        try:
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            break


def _get_logger() -> logging.BotLogger:
    return logging.get_logger("ProcessBotStateDumper")
