#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.

import enum
import typing

import pydantic
from fastapi import HTTPException, status


class AuthErrorCode(str, enum.Enum):
    AUTH_PASSPHRASE_REQUIRED = "auth_passphrase_required"
    AUTH_WALLET_ADDRESS_REQUIRED = "auth_wallet_address_required"
    AUTH_WALLET_NOT_FOUND = "auth_wallet_not_found"
    AUTH_INVALID_PASSPHRASE = "auth_invalid_passphrase"
    AUTH_NODE_NOT_CONFIGURED = "auth_node_not_configured"


class NodeAuthErrorDetail(pydantic.BaseModel):
    code: AuthErrorCode
    message: typing.Optional[str] = None


def auth_http_exception(
    status_code: int,
    code: AuthErrorCode,
    message: typing.Optional[str] = None,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail=NodeAuthErrorDetail(code=code, message=message).model_dump(),
    )


def node_not_configured_exception() -> HTTPException:
    return auth_http_exception(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        AuthErrorCode.AUTH_NODE_NOT_CONFIGURED,
        message="Node wallet is not configured",
    )
