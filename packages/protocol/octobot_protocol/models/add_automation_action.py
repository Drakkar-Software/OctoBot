# coding: utf-8

from __future__ import annotations
import json

from pydantic import ConfigDict, StrictStr
from typing import Any, ClassVar, Dict, List, Optional
from octobot_protocol.models.action_base import ActionBase
from typing import Optional, Set
from typing_extensions import Self


class AddAutomationAction(ActionBase):
    """
    Action to add or update an automation.
    automation field stored as Dict to avoid circular import with AutomationState.
    """
    action_type: StrictStr = "add_automation"
    automation: Dict[str, Any]
    __properties: ClassVar[List[str]] = ["id", "action_type", "status", "dsl", "result", "error", "completed_at", "automation"]

    model_config = ConfigDict(
        validate_by_name=True,
        validate_by_alias=True,
        validate_assignment=True,
        protected_namespaces=(),
    )

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
            "automation": obj.get("automation"),
        })
