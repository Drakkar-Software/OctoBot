#  Drakkar-Software OctoBot-Commons
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.*
import dataclasses
import pydantic
import enum
import datetime
import typing

import octobot_commons.dataclasses

import tests.dataclasses.pydantic_test_models as pydantic_test_models


_SAMPLE_ACCOUNT_UPDATED_AT = "2026-01-02T14:30:00"
_SAMPLE_AUTOMATION_UPDATED_AT = "2026-03-04T09:15:30"


def account_user_action_payload(*, error_details: str | None = "acct err"):
    """JSON-shape dict suitable for UserActionResult.from_dict (isoformat strings, enums as strings)."""
    return {
        "updated_at": _SAMPLE_ACCOUNT_UPDATED_AT,
        "result_type": "account",
        "error_details": error_details,
    }


def automation_user_action_payload(*, created_automation_id: str = "auto-new-42"):
    return {
        "updated_at": _SAMPLE_AUTOMATION_UPDATED_AT,
        "result_type": "automation",
        "created_automation_id": created_automation_id,
    }


@dataclasses.dataclass
class DualUserActionResultHolder(octobot_commons.dataclasses.MinimizableDataclass):
    account_outcome: pydantic_test_models.UserActionResult
    automation_outcome: pydantic_test_models.UserActionResult


@dataclasses.dataclass
class UserActionResultListHolder(octobot_commons.dataclasses.MinimizableDataclass):
    results: list[pydantic_test_models.UserActionResult] = dataclasses.field(default_factory=list)

    def __post_init__(self):
        if self.results and isinstance(self.results[0], dict):
            self.results = (
                [pydantic_test_models.UserActionResult.from_dict(entry) for entry in self.results]
                if self.results
                else []
            )


class JobType(enum.Enum):
    FULL_TIME = "full-time"
    PART_TIME = "part-time"


class Job(pydantic.BaseModel):
    id: int = 0
    name: str = ""
    description: typing.Optional[str] = None
    type: JobType = JobType.FULL_TIME
    created_at: datetime.datetime = datetime.datetime.now(datetime.timezone.utc)
    updated_at: typing.Optional[datetime.datetime] = None


@dataclasses.dataclass
class TestPersonClass(octobot_commons.dataclasses.MinimizableDataclass):
    name: str = ""
    age: int = 0
    job: Job = dataclasses.field(default_factory=Job)
    likes: list = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class TestPersonGroupClass(octobot_commons.dataclasses.MinimizableDataclass):
    identifier: str = ""
    present_people: list[TestPersonClass] = dataclasses.field(default_factory=list)
    absent_people: list[TestPersonClass] = dataclasses.field(default_factory=list)
    leader: TestPersonClass = dataclasses.field(default_factory=TestPersonClass)

    def __post_init__(self):
        if self.present_people and isinstance(self.present_people[0], dict):
            self.present_people = [TestPersonClass.from_dict(p) for p in self.present_people] if self.present_people else []
        if self.absent_people and isinstance(self.absent_people[0], dict):
            self.absent_people = [TestPersonClass.from_dict(p) for p in self.absent_people] if self.absent_people else []


def test_to_dict_include_default_values():
    """to_dict(include_default_values=True) returns full dict with all fields."""
    person = TestPersonClass(name="rhombur", age=33, job=Job(id=1, name="prince", description="Ixian prince", type=JobType.PART_TIME, created_at=datetime.datetime(2026, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)))
    result = person.to_dict(include_default_values=True)

    assert result == {
        "name": "rhombur",
        "age": 33,
        'job': {
            'id': 1,
            'name': 'prince',
            'description': 'Ixian prince',
            'type': 'part-time',
            'created_at': "2026-01-01T12:00:00Z",
        },
        "likes": [],
    }


def test_to_dict_exclude_default_values():
    """to_dict(include_default_values=False) returns only non-default values."""
    person = TestPersonClass(name="rhombur", age=33, job=Job(name="prince", description="Ixian prince", type=JobType.PART_TIME, created_at=datetime.datetime(2026, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)))
    result = person.to_dict(include_default_values=False)

    assert result == {
        "name": "rhombur",
        "age": 33,
        'job': {
            'name': 'prince',
            'description': 'Ixian prince',
            'type': 'part-time',
            'created_at': "2026-01-01T12:00:00Z",
        },
    }
    assert "likes" not in result


def test_to_dict_exclude_default_values_all_defaults():
    """to_dict(include_default_values=False) returns empty dict when all values are default."""
    person = TestPersonClass()
    result = person.to_dict(include_default_values=False)

    assert result == {}


def test_to_dict_exclude_default_values_nested():
    """to_dict(include_default_values=False) minimizes nested MinimizableDataclass instances."""
    leader = TestPersonClass(name="leto", age=25, job=Job(name="prince", description="Caladan prince", type=JobType.FULL_TIME))
    group = TestPersonGroupClass(identifier="atreides", leader=leader)

    result = group.to_dict(include_default_values=False)

    assert result["identifier"] == "atreides"
    assert result["leader"] == {
        "name": "leto", "age": 25, 
        'job': {'name': 'prince', 'description': 'Caladan prince'}
    }
    assert "present_people" not in result
    assert "absent_people" not in result


def test_to_dict_exclude_default_values_with_list():
    """to_dict(include_default_values=False) handles lists of MinimizableDataclass."""
    person = TestPersonClass(name="paul", age=15)
    group = TestPersonGroupClass(present_people=[person])

    result = group.to_dict(include_default_values=False)

    assert result["present_people"] == [{"name": "paul", "age": 15}]
    assert result["leader"] == {}
    assert "absent_people" not in result


def test_to_dict_roundtrip():
    """to_dict then from_dict preserves data."""
    person = TestPersonClass(name="chani", age=20, likes=["desert", "stillsuit"])
    as_dict = person.to_dict(include_default_values=True)
    restored = TestPersonClass.from_dict(as_dict)

    assert restored.name == person.name
    assert restored.age == person.age
    assert restored.likes == person.likes


def test_minimizable_to_dict_from_dict_polymorphic_user_action_results_round_trip():
    """MinimizableDataclass.to_dict + FlexibleDataclass.from_dict preserve oneOf discriminator payloads."""
    scalar_original = DualUserActionResultHolder(
        account_outcome=pydantic_test_models.UserActionResult.from_dict(account_user_action_payload()),
        automation_outcome=pydantic_test_models.UserActionResult.from_dict(automation_user_action_payload()),
    )
    scalar_flat = scalar_original.to_dict(include_default_values=True)
    scalar_restored = DualUserActionResultHolder.from_dict(scalar_flat)
    assert scalar_restored.account_outcome.actual_instance.model_dump(mode="json") == (
        scalar_original.account_outcome.actual_instance.model_dump(mode="json")
    )
    assert scalar_restored.automation_outcome.actual_instance.model_dump(mode="json") == (
        scalar_original.automation_outcome.actual_instance.model_dump(mode="json")
    )
    assert isinstance(scalar_restored.account_outcome.actual_instance, pydantic_test_models.AccountActionResult)
    assert isinstance(scalar_restored.automation_outcome.actual_instance, pydantic_test_models.AutomationActionResult)

    list_original = UserActionResultListHolder(
        results=[
            pydantic_test_models.UserActionResult.from_dict(
                account_user_action_payload(error_details="loop-a"),
            ),
            pydantic_test_models.UserActionResult.from_dict(
                automation_user_action_payload(created_automation_id="loop-b"),
            ),
        ],
    )
    list_flat = list_original.to_dict(include_default_values=True)
    list_restored = UserActionResultListHolder.from_dict(list_flat)
    assert len(list_restored.results) == len(list_original.results)
    for result_slot_index in range(len(list_original.results)):
        assert (
            list_restored.results[result_slot_index].actual_instance.model_dump(mode="json")
            == list_original.results[result_slot_index].actual_instance.model_dump(mode="json")
        )
