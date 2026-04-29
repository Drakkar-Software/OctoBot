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
import copy
import dataclasses

import octobot_commons.dataclasses


@dataclasses.dataclass
class TestPersonClass(octobot_commons.dataclasses.UpdatableDataclass):
    name: str = ""
    age: int = 0
    likes: list = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class TestPersonGroupClass(octobot_commons.dataclasses.UpdatableDataclass):
    identifier: str = ""
    present_people: list[TestPersonClass] = dataclasses.field(default_factory=list)
    absent_people: list[TestPersonClass] = dataclasses.field(default_factory=list)
    leader: TestPersonClass = dataclasses.field(default_factory=TestPersonClass)


def test_simple_update():
    person_1 = TestPersonClass("olive", 25)
    person_2 = TestPersonClass("olive", 25, ["football", "poe"])
    person_2_update = TestPersonClass("tom", likes=["football"])

    assert person_1.likes == []
    person_1.update(person_2)
    # no _updated_fields: no update
    assert person_1.name == "olive"
    assert person_1.age == 25
    assert person_1.likes == []
    person_2._updated_fields = ("name", "age", "likes")

    # _updated_fields is set: update
    person_1.update(person_2)
    assert person_1.name == "olive"
    assert person_1.age == 25
    assert person_1.likes == ["football", "poe"]

    person_2_update._updated_fields = ["name", "likes"]
    person_2.update(person_2_update)
    assert person_2.name == "tom"
    assert person_2.age == 25   # not in _updated_fields
    assert person_2.likes == ["football"]


def test_nested_update():
    person_1 = TestPersonClass("olive", 25)
    person_2 = TestPersonClass("olive", 25, ["football", "poe"])
    person_3 = TestPersonClass("mr plop", 29, ["crypto", "poe"])
    person_2_update = TestPersonClass("tom", likes=["football"], _updated_fields=["name", "likes"])
    group_1 = TestPersonGroupClass()    # empty group
    group_2 = TestPersonGroupClass(
        identifier="identifier_1",
        present_people=[person_1, person_3],
        absent_people=[person_2]
    )
    group_2_update_no_absent = TestPersonGroupClass(
        absent_people=[],
        _updated_fields=["absent_people"]
    )
    group_2_update_empty_identifier = TestPersonGroupClass(
        _updated_fields=["identifier"]
    )
    group_2_update_person_1 = TestPersonGroupClass(
        present_people=[person_2_update, person_3],
        _updated_fields=["present_people"]
    )

    assert group_1.identifier == ""
    assert group_1.present_people == []
    assert group_1.absent_people == []

    group_1.update(group_2)
    # no updated_fields
    assert group_1.identifier == ""
    assert group_1.present_people == []
    assert group_1.absent_people == []

    group_1.identifier = "plop"
    assert group_1.identifier == "plop"
    group_1.update(group_2_update_empty_identifier)
    assert group_1.identifier == ""     # updated
    assert group_1.present_people == []
    assert group_1.absent_people == []

    assert len(group_2.absent_people) == 1
    group_2.update(group_2_update_no_absent)
    assert group_2.absent_people == []    # updated

    assert group_2.identifier == "identifier_1"
    group_2.update(group_2_update_empty_identifier)
    assert group_2.identifier == ""    # updated

    assert group_2.present_people[0].name == "olive"
    assert group_2.present_people[0].age == 25
    assert group_2.present_people[0].likes == []
    assert group_2.present_people[1].name == "mr plop"
    assert group_2.present_people[1].age == 29
    assert group_2.present_people[1].likes == ["crypto", "poe"]
    group_2.update(group_2_update_person_1)
    assert group_2.present_people[0].name == "tom"  # updated
    assert group_2.present_people[0].age == 25
    assert group_2.present_people[0].likes == ["football"]  # updated
    assert group_2.present_people[1].name == "mr plop"
    assert group_2.present_people[1].age == 29
    assert group_2.present_people[1].likes == ["crypto", "poe"]

    group_2_update_person_2 = TestPersonGroupClass(
        present_people=[person_2_update],
        _updated_fields=["present_people"]
    )
    group_2.update(group_2_update_person_2)
    # group_2.present_people[1] got removed
    assert len(group_2.present_people) == 1
    assert group_2.present_people[0].name == "tom"
    assert group_2.present_people[0].age == 25
    assert group_2.present_people[0].likes == ["football"]

    group_2.update(group_2_update_person_1)
    # group_2.present_people[1] is added back
    assert group_2.present_people[0].name == "tom"  # updated
    assert group_2.present_people[0].age == 25
    assert group_2.present_people[0].likes == ["football"]  # updated
    assert group_2.present_people[1].name == "mr plop"
    assert group_2.present_people[1].age == 29
    assert group_2.present_people[1].likes == ["crypto", "poe"]


def test_get_update():
    person_1 = TestPersonClass("olive", 25)
    person_2 = TestPersonClass("olive", 25, ["football", "poe"])
    person_3 = TestPersonClass("mr plop", 29, ["crypto", "poe"])

    # only likes changed
    update = person_1.get_update(person_2)
    assert update.name == ""
    assert update.age == 0
    assert update.likes == ["football", "poe"]
    assert update._updated_fields == ["likes"]

    # everything changed
    update = person_1.get_update(person_3)
    assert update.name == "mr plop"
    assert update.age == 29
    assert update.likes == ["crypto", "poe"]
    assert update._updated_fields == ["name", "age", "likes"]

    # likes got removed
    update = person_2.get_update(person_1)
    assert update.name == ""
    assert update.age == 0
    assert update.likes == []
    assert update._updated_fields == ["likes"]


def test_nested_get_update():
    person_1 = TestPersonClass("olive", 25)
    person_2 = TestPersonClass("olive", 25, ["football", "poe"])
    person_3 = TestPersonClass("mr plop", 29, ["crypto", "poe"])
    person_3_update = TestPersonClass("mr plop the second", 10, ["crypto", "poe", "metal"])
    group_1 = TestPersonGroupClass()    # empty group
    group_2 = TestPersonGroupClass(
        identifier="identifier_1",
        present_people=[person_1, person_3],
        absent_people=[person_2],
        leader=person_1,
    )
    group_3 = TestPersonGroupClass(
        identifier="identifier_1",
        present_people=[person_1],
        absent_people=[person_2, person_3],
        leader=person_3,
    )
    group_3_updated_person_3 = TestPersonGroupClass(
        identifier="identifier_1",
        present_people=[person_1],
        absent_people=[person_2, person_3_update],
        leader=person_3_update,
    )

    update = group_1.get_update(group_1)
    assert update._updated_fields == []

    update = group_2.get_update(group_2)
    assert update._updated_fields == []

    update = group_1.get_update(group_2)
    assert update.identifier == "identifier_1"
    assert update.present_people == [person_1, person_3]
    assert update.absent_people == [person_2]
    assert update.leader.name == "olive"
    assert update.leader.age == 25
    assert update.leader._updated_fields == ["name", "age"]
    assert update._updated_fields == ["identifier", "present_people", "absent_people", "leader"]

    update = group_2.get_update(group_1)
    assert update.identifier == ""
    assert update.present_people == []
    assert update.absent_people == []
    assert update.leader.name == ""
    assert update.leader.age == 0
    assert update.leader.likes == []
    assert update.leader._updated_fields == ["name", "age"]
    assert update._updated_fields == ["identifier", "present_people", "absent_people", "leader"]

    update = group_2.get_update(group_3)
    assert update.identifier == ""
    assert update.present_people == [TestPersonClass()]             # TestPersonClass() when no change
    assert update.absent_people == [TestPersonClass(), person_3]    # TestPersonClass() when no change
    assert update.leader.name == person_3.name
    assert update.leader.age == person_3.age
    assert update.leader.likes == person_3.likes
    assert update.leader._updated_fields == ["name", "age", "likes"]
    assert update._updated_fields == ["present_people", "absent_people", "leader"]

    update = group_3.get_update(group_3_updated_person_3)
    assert update.identifier == ""
    assert update.present_people == []
    assert len(update.absent_people) == 2
    assert update.absent_people[0] == TestPersonClass()
    assert update.absent_people[1].name == person_3_update.name
    assert update.absent_people[1].age == person_3_update.age
    assert update.absent_people[1].likes == person_3_update.likes
    assert update.absent_people[1]._updated_fields == ["name", "age", "likes"]
    assert update._updated_fields == ["absent_people", "leader"]
    assert update.leader.name == person_3_update.name
    assert update.leader.age == person_3_update.age
    assert update.leader.likes == person_3_update.likes
    assert update.leader._updated_fields == ["name", "age", "likes"]


def test_get_update_and_update():
    person_1 = TestPersonClass("olive", 25)
    person_2 = TestPersonClass("olive", 25, likes=["football", "poe"])
    person_3 = TestPersonClass("mr plop", 29, ["crypto", "poe"])
    group_1 = TestPersonGroupClass()    # empty group
    group_2 = TestPersonGroupClass(
        identifier="identifier_1",
        present_people=[person_1, person_3],
        absent_people=[person_2],
        leader=copy.deepcopy(person_1),
    )
    group_3 = TestPersonGroupClass(
        identifier="identifier_1",
        present_people=[person_1],
        absent_people=[person_2, person_3],
        leader=copy.deepcopy(person_3),
    )

    person_1_2 = copy.deepcopy(person_1)
    person_1_2.update(person_1.get_update(person_2))
    assert person_1_2.name == person_1.name
    assert person_1_2.age == person_1.age
    assert person_1_2.likes == person_2.likes
    assert person_1_2._updated_fields == []

    person_3_1 = copy.deepcopy(person_3)
    person_3_1.update(person_3.get_update(person_1))
    assert person_3_1.name == person_1.name
    assert person_3_1.age == person_1.age
    assert person_3_1.likes == person_1.likes
    assert person_3_1._updated_fields == []

    group_2_3 = copy.deepcopy(group_2)
    update = group_2.get_update(group_3)
    assert update.identifier == ""
    assert update.present_people == [TestPersonClass()]
    assert len(update.absent_people) == 2
    assert update.absent_people[0] == TestPersonClass()
    assert update.absent_people[1].name == person_3.name
    assert update.leader.name == person_3.name
    group_2_3.update(update)
    assert group_2_3.identifier == group_2.identifier
    assert group_2_3.present_people == group_3.present_people
    assert group_2_3.absent_people == group_3.absent_people
    assert group_2_3.leader == group_3.leader


def test_to_dict_without_updated_fields():
    person_2 = TestPersonClass("olive", 25, likes=["football", "poe"])
    # _updated_fields included (default behavior)
    assert dataclasses.asdict(person_2) == {
        "_updated_fields": [],
        "name": "olive",
        "age": 25,
        "likes": ["football", "poe"]
    }
    # _updated_fields not included
    assert person_2.to_dict_without_updated_fields() == {
        "name": "olive",
        "age": 25,
        "likes": ["football", "poe"]
    }
