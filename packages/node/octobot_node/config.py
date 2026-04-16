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

import sys
from typing import Annotated, Any, Literal

from pydantic import (
    AnyUrl,
    BeforeValidator,
    HttpUrl,
    computed_field,
    Field,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


def _get_env_file() -> str:
    # Check if pytest module is imported
    if "pytest" in sys.modules:
        return ".env.test"
    return ".env"


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",") if i.strip()]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


def parse_key_to_bytes(v: str | bytes | None) -> bytes | None:
    if v is None:
        return None
    if isinstance(v, bytes):
        return v
    return v.encode('utf-8')


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Use .env.test when running tests, otherwise use .env
        env_file=_get_env_file(),
        env_ignore_empty=True,
        extra="ignore",
    )
    NODE_ENVIRONMENT: Literal["local", "production"] = "production"
    BACKEND_HOST: str = "http://localhost:8000"
    FRONTEND_HOST: str = "http://localhost:5173" if NODE_ENVIRONMENT == "local" else BACKEND_HOST

    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS] + [
            self.FRONTEND_HOST
        ]

    SENTRY_DSN: HttpUrl | None = None
    SCHEDULER_POSTGRES_URL: AnyUrl | None = None  # examplee: postgresql://postgres:password@localhost:5432/dbos_example
    SCHEDULER_SQLITE_FILE: str = "tasks.db" # example tasks.db
    IS_MASTER_MODE: bool = False  # True: start OctoBot Node as master (enables master-side features)
    CONSUMER_ONLY: bool = False  # True: start OctoBot Node in consumer mode only (requires a postgres database)
    SCHEDULER_MAX_EXECUTOR_THREADS: int = 200 #todo reduce after dbos 2.13.0 is released
    POSTGRES_STORAGE_CERTS_PATH: str | None = None

    # Task encryption keys (server-side)
    TASKS_INPUTS_RSA_PRIVATE_KEY: Annotated[bytes | None, BeforeValidator(parse_key_to_bytes)] = None
    TASKS_INPUTS_ECDSA_PUBLIC_KEY: Annotated[bytes | None, BeforeValidator(parse_key_to_bytes)] = None
    TASKS_INPUTS_RSA_PUBLIC_KEY: Annotated[bytes | None, BeforeValidator(parse_key_to_bytes)] = None
    TASKS_INPUTS_ECDSA_PRIVATE_KEY: Annotated[bytes | None, BeforeValidator(parse_key_to_bytes)] = None

    USE_DEDICATED_LOG_FILE_PER_AUTOMATION: bool = True

    @computed_field
    @property
    def is_node_side_encryption_enabled(self) -> bool:
        return all([
            self.TASKS_INPUTS_RSA_PRIVATE_KEY,
            self.TASKS_INPUTS_ECDSA_PUBLIC_KEY,
            self.TASKS_INPUTS_RSA_PUBLIC_KEY,
            self.TASKS_INPUTS_ECDSA_PRIVATE_KEY,
        ])

    @computed_field
    @property
    def tasks_encryption_enabled(self) -> bool:
        return self.is_node_side_encryption_enabled


settings = Settings()  # type: ignore
