# coding: utf-8

from __future__ import annotations
import json

from pydantic import ConfigDict, StrictStr
from typing import Any, ClassVar, Dict, List, Optional
from octobot_protocol.models.action_base import ActionBase
from octobot_protocol.models.account import Account
from typing import Optional, Set
from typing_extensions import Self
from pydantic_core import to_jsonable_python


class AddExchangeAccountAction(ActionBase):
    """
    Action to add or update an account.
    """
    action_type: StrictStr = "add_exchange_account"
    account: Account
    __properties: ClassVar[List[str]] = ["id", "action_type", "status", "dsl", "result", "error", "completed_at", "account"]

    model_config = ConfigDict(
        validate_by_name=True,
        validate_by_alias=True,
        validate_assignment=True,
        protected_namespaces=(),
    )

    def to_dict(self) -> Dict[str, Any]:
        excluded_fields: Set[str] = set()
        _dict = self.model_dump(by_alias=True, exclude=excluded_fields, exclude_none=True)
        if self.account:
            _dict['account'] = self.account.to_dict()
        return _dict

    @classmethod
    def from_dict(cls, obj: Optional[Dict[str, Any]]) -> Optional[Self]:
        if obj is None:
            return None
        if not isinstance(obj, dict):
            return cls.model_validate(obj)
        return cls.model_validate({
            "id": obj.get("id"),
            "action_type": obj.get("action_type"),
            "status": obj.get("status"),
            "dsl": obj.get("dsl"),
            "result": obj.get("result"),
            "error": obj.get("error"),
            "completed_at": obj.get("completed_at"),
            "account": Account.from_dict(obj["account"]) if obj.get("account") is not None else None,
        })
