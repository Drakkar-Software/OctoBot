# coding: utf-8

from __future__ import annotations
import pprint
import json

from datetime import datetime
from pydantic import BaseModel, ConfigDict, StrictStr
from typing import Any, ClassVar, Dict, List, Optional
from octobot_protocol.models.task_status import TaskStatus
from typing import Optional, Set
from typing_extensions import Self
from pydantic_core import to_jsonable_python


class ActionBase(BaseModel):
    """
    Common base fields shared by all Action subtypes.
    """
    id: StrictStr
    action_type: StrictStr
    status: TaskStatus
    dsl: Optional[StrictStr] = None
    result: Optional[StrictStr] = None
    error: Optional[StrictStr] = None
    completed_at: Optional[datetime] = None
    __properties: ClassVar[List[str]] = ["id", "action_type", "status", "dsl", "result", "error", "completed_at"]

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

    @classmethod
    def from_json(cls, json_str: str) -> Optional[Self]:
        return cls.from_dict(json.loads(json_str))

    def to_dict(self) -> Dict[str, Any]:
        excluded_fields: Set[str] = set()
        return self.model_dump(by_alias=True, exclude=excluded_fields, exclude_none=True)

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
        })
