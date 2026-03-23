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

import uuid
import typing
import datetime
from enum import Enum

from pydantic import BaseModel, Field


class UserBase(BaseModel):
    email: str = Field(max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


class User(UserBase):
    id: uuid.UUID


class TaskStatus(str, Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    PERIODIC = "periodic"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskType(str, Enum):
    EXECUTE_ACTIONS = "execute_actions"

class Execution(BaseModel):
    id: str
    name: typing.Optional[str] = None
    description: typing.Optional[str] = None
    actions: typing.Optional[str] = None
    type: typing.Optional[str] = None
    status: typing.Optional[TaskStatus] = None
    result: typing.Optional[str] = None
    result_metadata: typing.Optional[str] = None
    scheduled_at: typing.Optional[datetime.datetime] = None
    completed_at: typing.Optional[datetime.datetime] = None


class Task(BaseModel):
    id: str = str(uuid.uuid4())
    name: typing.Optional[str] = None
    content: typing.Optional[str] = None
    content_metadata: typing.Optional[str] = None
    type: typing.Optional[str] = None
    result: typing.Optional[typing.Any] = None
    result_metadata: typing.Optional[str] = None
    executions: list[Execution] = []

class Node(BaseModel):
    node_type: str
    backend_type: str
    workers: int | None
    status: str
    redis_url: str | None = None
    sqlite_file: str | None = None
