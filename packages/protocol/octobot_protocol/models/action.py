# coding: utf-8

from __future__ import annotations
import json
import pprint

from datetime import datetime
from pydantic import BaseModel, ConfigDict, StrictStr
from typing import Any, ClassVar, Dict, List, Optional, Union
from octobot_protocol.models.action_base import ActionBase
from octobot_protocol.models.add_exchange_account_action import AddExchangeAccountAction
from octobot_protocol.models.remove_exchange_account_action import RemoveExchangeAccountAction
from octobot_protocol.models.add_automation_action import AddAutomationAction
from octobot_protocol.models.remove_automation_action import RemoveAutomationAction
from octobot_protocol.models.task_status import TaskStatus
from typing import Optional, Set
from typing_extensions import Self
from pydantic_core import to_jsonable_python

# Union type for all Action subtypes.
ActionUnion = Union[
    AddExchangeAccountAction,
    RemoveExchangeAccountAction,
    AddAutomationAction,
    RemoveAutomationAction,
]


class Action(ActionBase):
    """
    Backward-compatible dispatcher. from_dict dispatches to the correct subtype based on action_type.
    Falls back to ActionBase when action_type is unknown.
    """
    dsl: Optional[StrictStr] = None
    result: Optional[StrictStr] = None
    error: Optional[StrictStr] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(
        validate_by_name=True,
        validate_by_alias=True,
        validate_assignment=True,
        protected_namespaces=(),
    )

    def to_str(self) -> str:
        return pprint.pformat(self.model_dump(by_alias=True))

    def to_json(self) -> str:
        return json.dumps(to_jsonable_python(self.to_dict()))

    def to_dict(self) -> Dict[str, Any]:
        excluded_fields: Set[str] = set()
        return self.model_dump(by_alias=True, exclude=excluded_fields, exclude_none=True)

    @classmethod
    def from_json(cls, json_str: str) -> Optional[ActionUnion]:
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def from_dict(cls, obj: Optional[Dict[str, Any]]) -> Optional[ActionUnion]:
        """Dispatch to the correct Action subtype based on action_type."""
        if obj is None:
            return None
        if not isinstance(obj, dict):
            action_type = getattr(obj, "action_type", None)
        else:
            action_type = obj.get("action_type", "")

        if action_type == "add_exchange_account":
            return AddExchangeAccountAction.from_dict(obj)
        if action_type == "remove_exchange_account":
            return RemoveExchangeAccountAction.from_dict(obj)
        if action_type == "add_automation":
            return AddAutomationAction.from_dict(obj)
        if action_type == "remove_automation":
            return RemoveAutomationAction.from_dict(obj)

        # Fallback: parse as base Action fields.
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
        })
