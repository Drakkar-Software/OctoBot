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

import logging
import os
import threading
import time
import typing

import pydantic
import octobot_services.constants as services_constants
import octobot_services.interfaces.util as interfaces_util
from fastapi import APIRouter, HTTPException, status

import octobot_node.config
import octobot_node.constants
import octobot_node.models
import octobot_node.scheduler.api
import octobot_node.scheduler.scheduler

try:
    from tentacles.Services.Interfaces.node_api_interface.api.deps import AdminUser, CurrentUser
except ImportError:
    from api.deps import AdminUser, CurrentUser  # type: ignore[no-redef]

try:
    import octobot_commons.logging.context_based_file_handler as context_based_file_handler
except ImportError:
    context_based_file_handler = None

# Service_bases is only needed at runtime, not for build (see node_api.py).
try:
    import tentacles.Services.Services_bases.node_api_service.node_api as node_api_service_module
except ImportError:
    node_api_service_module = None

router = APIRouter(tags=["nodes"])


class NodeConfigUpdate(pydantic.BaseModel):
    node_type: typing.Optional[typing.Literal["standalone", "master"]] = None
    use_dedicated_log_file_per_automation: typing.Optional[bool] = None
    external_host: typing.Optional[str] = None
    cloud_sync_enabled: typing.Optional[bool] = None
    cloud_sync_collections: typing.Optional[typing.List[str]] = None


@router.get("/me", response_model=octobot_node.models.Node)
def get_current_node(current_user: CurrentUser) -> typing.Any:
    status = octobot_node.scheduler.api.get_node_status()
    return octobot_node.models.Node(**status)


@router.get("/config")
def get_node_config(current_user: CurrentUser) -> typing.Any:
    return {
        "node_type": "master" if octobot_node.config.settings.IS_MASTER_MODE else "standalone",
        "use_dedicated_log_file_per_automation": octobot_node.config.settings.USE_DEDICATED_LOG_FILE_PER_AUTOMATION,
        "tasks_encryption_enabled": octobot_node.config.settings.tasks_encryption_enabled,
        "server_encryption_env_vars": octobot_node.constants.TASKS_ENCRYPTION_ENV_VARS,
        "external_host": (
            node_api_service_module.NodeApiService.instance().get_node_external_host()
            if node_api_service_module else None
        ),
        "external_host_env_override": bool(os.getenv(services_constants.ENV_NODE_EXTERNAL_HOST)),
        "cloud_sync_enabled": (
            node_api_service_module.NodeApiService.instance().get_cloud_sync_enabled()
            if node_api_service_module else False
        ),
        "cloud_sync_collections": (
            node_api_service_module.NodeApiService.instance().get_cloud_sync_collections()
            if node_api_service_module else []
        ),
    }


def _schedule_stop_bot(delay_seconds: float = 0.1) -> None:
    def _delayed_stop() -> None:
        time.sleep(delay_seconds)
        interfaces_util.get_bot_api().stop_bot()

    threading.Thread(target=_delayed_stop, daemon=True).start()


@router.post("/stop", status_code=status.HTTP_204_NO_CONTENT)
def stop_node(current_user: AdminUser) -> None:
    _schedule_stop_bot()


@router.patch("/config")
def update_node_config(config: NodeConfigUpdate, current_user: CurrentUser) -> typing.Any:
    if config.node_type is not None:
        octobot_node.config.settings.IS_MASTER_MODE = config.node_type == "master"
    if config.use_dedicated_log_file_per_automation is not None:
        octobot_node.config.settings.USE_DEDICATED_LOG_FILE_PER_AUTOMATION = config.use_dedicated_log_file_per_automation
        if config.use_dedicated_log_file_per_automation:
            octobot_node.scheduler.scheduler.Scheduler._setup_workflow_logging()
        else:
            _remove_context_based_file_handlers()
    if config.external_host is not None and node_api_service_module is not None:
        node_api_service_module.NodeApiService.instance().set_node_external_host(config.external_host)
    if config.cloud_sync_enabled is not None and node_api_service_module is not None:
        node_api_service_module.NodeApiService.instance().set_cloud_sync_enabled(config.cloud_sync_enabled)
    if config.cloud_sync_collections is not None and node_api_service_module is not None:
        try:
            node_api_service_module.NodeApiService.instance().set_cloud_sync_collections(
                config.cloud_sync_collections
            )
        except ValueError as err:
            raise HTTPException(status_code=400, detail=str(err))
    return get_node_config(current_user)


def _remove_context_based_file_handlers() -> None:
    if context_based_file_handler is None:
        return
    root_logger = logging.getLogger()
    to_remove = [
        h for h in root_logger.handlers
        if isinstance(h, context_based_file_handler.ContextBasedFileHandler)
    ]
    for handler in to_remove:
        handler.close()
        root_logger.removeHandler(handler)
