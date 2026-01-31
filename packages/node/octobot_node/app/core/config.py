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
import secrets
import sys
from typing import Annotated, Any, Literal

from pydantic import (
    AnyUrl,
    BeforeValidator,
    EmailStr,
    HttpUrl,
    computed_field,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self


DEFAULT_ADMIN_USERNAME: EmailStr = "admin@example.com"
DEFAULT_ADMIN_PASSWORD: str = "changethis"

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
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    ENVIRONMENT: Literal["local", "production"] = "production"
    BACKEND_HOST: str = "http://localhost:8000"
    FRONTEND_HOST: str = "http://localhost:5173" if ENVIRONMENT == "local" else BACKEND_HOST

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
    SCHEDULER_REDIS_URL: AnyUrl | None = None
    SCHEDULER_SQLITE_FILE: str = "tasks.db"
    SCHEDULER_WORKERS: int = 0  # 0 disables consumers, >0 enables consumers
    IS_MASTER_MODE: bool = False  # Enable master node mode
    REDIS_STORAGE_CERTS_PATH: str | None = None

    ADMIN_USERNAME: EmailStr = DEFAULT_ADMIN_USERNAME
    ADMIN_PASSWORD: str = DEFAULT_ADMIN_PASSWORD

    # Used to decrypt inputs and encrypt outputs
    TASKS_INPUTS_RSA_PRIVATE_KEY: Annotated[bytes | None, BeforeValidator(parse_key_to_bytes)] = None
    TASKS_INPUTS_ECDSA_PUBLIC_KEY: Annotated[bytes | None, BeforeValidator(parse_key_to_bytes)] = None
    TASKS_OUTPUTS_RSA_PUBLIC_KEY: Annotated[bytes | None, BeforeValidator(parse_key_to_bytes)] = None
    TASKS_OUTPUTS_ECDSA_PRIVATE_KEY: Annotated[bytes | None, BeforeValidator(parse_key_to_bytes)] = None

    # Used to encrypt inputs and decrypt outputs
    TASKS_INPUTS_RSA_PUBLIC_KEY: Annotated[bytes | None, BeforeValidator(parse_key_to_bytes)] = None
    TASKS_INPUTS_ECDSA_PRIVATE_KEY: Annotated[bytes | None, BeforeValidator(parse_key_to_bytes)] = None
    TASKS_OUTPUTS_RSA_PRIVATE_KEY: Annotated[bytes | None, BeforeValidator(parse_key_to_bytes)] = None
    TASKS_OUTPUTS_ECDSA_PUBLIC_KEY: Annotated[bytes | None, BeforeValidator(parse_key_to_bytes)] = None

    def _check_default_secret(self, var_name: str, value: str | None, default_value: EmailStr | None) -> None:
        if value == default_value:
            message = (
                f'The value of {var_name} is "{default_value}", '
                "for security, please change it, at least for deployments."
            )
            if self.ENVIRONMENT == "local":
                logging.getLogger("Settings").warning(message)
            else:
                raise ValueError(message)

    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        if self.IS_MASTER_MODE:
            self._check_default_secret("ADMIN_USERNAME", self.ADMIN_USERNAME, DEFAULT_ADMIN_USERNAME)
            self._check_default_secret(
                "ADMIN_PASSWORD", self.ADMIN_PASSWORD, DEFAULT_ADMIN_PASSWORD
            )
        return self


settings = Settings()  # type: ignore