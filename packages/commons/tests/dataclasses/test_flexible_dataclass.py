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

import octobot_commons.dataclasses


@dataclasses.dataclass
class TestPersonClass(octobot_commons.dataclasses.FlexibleDataclass):
    name: str = ""
    age: int = 0
    likes: list = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class TestPersonGroupClass(octobot_commons.dataclasses.FlexibleDataclass):
    identifier: str = ""
    present_people: list[TestPersonClass] = dataclasses.field(default_factory=list)
    absent_people: list[TestPersonClass] = dataclasses.field(default_factory=list)
    leader: TestPersonClass = dataclasses.field(default_factory=TestPersonClass)

    def __post_init__(self):
        if self.present_people and isinstance(self.present_people[0], dict):
            self.present_people = [TestPersonClass.from_dict(p) for p in self.present_people] if self.present_people else []
        if self.absent_people and isinstance(self.absent_people[0], dict):
            self.absent_people = [TestPersonClass.from_dict(p) for p in self.absent_people] if self.absent_people else []


def test_from_dict():
    person_1 = TestPersonClass(name="rhombur", age=33)
    dict_1 = dataclasses.asdict(person_1)
    person_1_1 = TestPersonClass.from_dict(dict_1)
    assert list(person_1_1.get_field_names()) == list(person_1.get_field_names()) == ['name', 'age', 'likes']
    assert person_1 == person_1_1
    person_1_1.name = "leto"

    group_1 = TestPersonGroupClass(identifier="plop", absent_people=[person_1], leader=person_1_1)
    dict_group = dataclasses.asdict(group_1)
    assert TestPersonGroupClass.from_dict(dict_group) == group_1

    # added values are not an issue
    dict_group["new_attr"] = 1
    dict_group["absent_people"][0]["other_attr"] = None
    dict_group["leader"].pop("age", None)
    dict_group["leader"]["age2"] = 22

    new_group = TestPersonGroupClass.from_dict(dict_group)
    assert new_group.leader.age == 0    # default value


def test_default_values():
    group_0 = TestPersonGroupClass()
    group_0_1 = TestPersonGroupClass()

    assert group_0.leader.name == group_0_1.leader.name
    assert group_0.leader is not group_0_1.leader
    group_0.leader.name = "erasme"
    assert group_0.leader.name != group_0_1.leader.name


def test_get_field_names():
    person_1 = TestPersonClass()
    person_2 = TestPersonClass()
    group_1 = TestPersonGroupClass()
    group_2 = TestPersonGroupClass()

    assert list(person_1.get_field_names()) == list(person_2.get_field_names()) == ['name', 'age', 'likes']
    assert list(group_1.get_field_names()) == list(group_2.get_field_names()) == \
       ['identifier', 'present_people', 'absent_people', 'leader']
