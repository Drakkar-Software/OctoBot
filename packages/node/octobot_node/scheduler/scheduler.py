#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
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

from huey import Huey, RedisHuey, SqliteHuey
from huey.registry import Message
from huey.utils import Error as HueyError

import typing
import logging
import pickle
import json
import octobot_node.models
import octobot_node.enums
import octobot_node.config

DEFAULT_NAME = "octobot_node"

class Scheduler:
    INSTANCE: typing.Optional[Huey] = None

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def create(self):
        if octobot_node.config.settings.SCHEDULER_REDIS_URL:
            import redis
            self.logger.info(
                "Initializing scheduler with Redis backend at %s", octobot_node.config.settings.SCHEDULER_REDIS_URL
            )

            connection_pool = redis.ConnectionPool.from_url(
                str(octobot_node.config.settings.SCHEDULER_REDIS_URL),
                ssl_ca_certs=f"{octobot_node.config.settings.REDIS_STORAGE_CERTS_PATH}/ca.crt",
                ssl_certfile=f"{octobot_node.config.settings.REDIS_STORAGE_CERTS_PATH}/client/client.crt",
                ssl_keyfile=f"{octobot_node.config.settings.REDIS_STORAGE_CERTS_PATH}/client/client.key",
                ssl_cert_reqs="required",
                decode_responses=False,
                socket_timeout=5,
                socket_connect_timeout=3
            ) if octobot_node.config.settings.REDIS_STORAGE_CERTS_PATH is not None else None

            self.INSTANCE = RedisHuey(DEFAULT_NAME, connection_pool=connection_pool) if connection_pool is not None else RedisHuey(DEFAULT_NAME, url=str(octobot_node.config.settings.SCHEDULER_REDIS_URL))
        else:
            self.logger.info(
                "Initializing scheduler with sqlite backend at %s", octobot_node.config.settings.SCHEDULER_SQLITE_FILE
            )
            self.INSTANCE = SqliteHuey(DEFAULT_NAME, filename=octobot_node.config.settings.SCHEDULER_SQLITE_FILE)

    def stop(self) -> None:
        if self.INSTANCE:
            # TODO self.INSTANCE.stop()
            self.logger.info("Scheduler stopped")
        else:
            self.logger.warning("Scheduler not initialized")

    def get_periodic_tasks(self) -> list[dict]:
        tasks: list[dict] = []
        periodic_tasks = self.INSTANCE._registry.periodic_tasks
        for task in periodic_tasks or []:
            try:
                tasks.append(self._parse_task(task, octobot_node.models.TaskStatus.PERIODIC, f"Periodic task: {task.name}"))
            except Exception as e:
                self.logger.warning(f"Failed to process periodic task {task.name}: {e}")
        return tasks

    def get_pending_tasks(self) -> list[dict]:
        tasks: list[dict] = []
        pending_tasks = self.INSTANCE.pending()
        for task in pending_tasks or []:
            try:
                tasks.append(self._parse_task(task, octobot_node.models.TaskStatus.PENDING, f"Pending task: {task.name}"))
            except Exception as e:
                self.logger.warning(f"Failed to process pending task {task.name}: {e}")
        return tasks

    def get_scheduled_tasks(self) -> list[dict]:
        tasks: list[dict] = []
        scheduled_tasks = self.INSTANCE.scheduled()
        for task in scheduled_tasks or []:
            try:
                tasks.append(self._parse_task(task, octobot_node.models.TaskStatus.SCHEDULED, f"Scheduled at {task.eta.strftime('%Y-%m-%d %H:%M:%S')}"))
            except Exception as e:
                self.logger.warning(f"Failed to process scheduled task {task.name}: {e}")
        return tasks

    def _decode_result(self, result_key_bytes: bytes | str, result_value_bytes: bytes | typing.Any) -> tuple[str, typing.Any | None]:
        task_id = result_key_bytes.decode('utf-8') if isinstance(result_key_bytes, bytes) else result_key_bytes
        
        try:
            result_obj = pickle.loads(result_value_bytes) if isinstance(result_value_bytes, bytes) else result_value_bytes
            return (task_id, result_obj)
        except (pickle.UnpicklingError, Exception) as unpickle_error:
            self.logger.warning(f"Failed to unpickle result for task {task_id}: {unpickle_error}")
            return (task_id, None)

    def get_results(self) -> list[dict]:
        tasks: list[dict] = []
        result_keys = self.INSTANCE.all_results()
        for result_key_bytes, result_value_bytes in result_keys.items():
            try:
                task_id, result_obj = self._decode_result(result_key_bytes, result_value_bytes)
                
                if result_obj is None:
                    description = f"Task completed (unable to parse result)"
                    status = octobot_node.models.TaskStatus.COMPLETED
                    result = ""
                    metadata = ""
                elif isinstance(result_obj, HueyError):
                    description = f"Task failed: {result_obj.metadata.get('error')}"
                    status = octobot_node.models.TaskStatus.FAILED
                    result = ""
                    metadata = ""
                else:
                    description = f"Task completed"
                    status = octobot_node.models.TaskStatus.COMPLETED
                    result = result_obj.get(octobot_node.enums.TaskResultKeys.RESULT.value)
                    metadata = result_obj.get(octobot_node.enums.TaskResultKeys.METADATA.value)

                tasks.append({
                    "id": task_id,
                    "name": self.get_task_name(result_obj, task_id),
                    "description": description,
                    "status": status,
                    "result": json.dumps(result),
                    "result_metadata": metadata,
                    "scheduled_at": None,
                    "started_at": None,
                    "completed_at": None,
                })
            except Exception as e:
                self.logger.warning(f"Failed to process result key {result_key_bytes}: {e}")
        return tasks


    def _parse_task(self, message: Message, status: octobot_node.models.TaskStatus, description: typing.Optional[str] = None) -> octobot_node.models.Task:
        task_kwargs = message.kwargs
        task_args = message.args
        task_actions = task_kwargs.get("actions")
        task_type = task_kwargs.get("type")
        task_name = self.get_task_name(task_args[0] if task_args and len(task_args) > 0 else {}, message.name)

        return octobot_node.models.Task(
            id=message.id,
            name=task_name,
            description=description,
            actions=task_actions,
            type=octobot_node.models.TaskType(task_type) if task_type else None,
            status=status,
            retries=message.retries,
            retry_delay=message.retry_delay,
            priority=message.priority,
            expires=message.expires,
            expires_resolved=message.expires_resolved,
            scheduled_at=message.eta,
            started_at=None,
            completed_at=None,
        )


    def save_data(self, key: str, value: str) -> None:
        self.INSTANCE.storage.put_data(key, value)

    def get_data(self, key: str) -> str:
        return self.INSTANCE.storage.peek_data(key)

    def get_task_name(self, task_data: dict | octobot_node.models.Task | None, default_value: typing.Optional[str] = None) -> typing.Optional[str]:
        if isinstance(task_data, octobot_node.models.Task):
            return task_data.name
        elif isinstance(task_data, dict):
            return task_data.get(octobot_node.enums.TaskResultKeys.TASK.value, {}).get("name", default_value)
        else:
            return default_value
