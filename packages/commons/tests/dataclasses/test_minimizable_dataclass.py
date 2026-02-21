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
