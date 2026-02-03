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
#  License along with this library.

from octobot_commons.tentacles_management.class_inspector import default_parent_inspection, default_parents_inspection, \
    get_class_from_parent_subclasses, get_deep_class_from_parent_subclasses, \
    is_abstract_using_inspection_and_class_naming, get_all_classes_from_parent, get_single_deepest_child_class


class AbstractParent:
    pass


class Parent(AbstractParent):
    pass


class BasicChild(Parent):
    pass


class ChildOfChild(BasicChild):
    pass


def test_default_parent_inspection():
    assert default_parent_inspection(BasicChild, Parent)
    assert not default_parent_inspection(ChildOfChild, Parent)
    assert default_parent_inspection(ChildOfChild, BasicChild)
    assert not default_parent_inspection(BasicChild, ChildOfChild)


def test_default_parents_inspection():
    assert default_parents_inspection(BasicChild, Parent)
    assert default_parents_inspection(ChildOfChild, Parent)
    assert default_parents_inspection(ChildOfChild, BasicChild)
    assert not default_parents_inspection(BasicChild, ChildOfChild)


def test_get_class_from_parent_subclasses():
    assert get_class_from_parent_subclasses("BasicChild", Parent) is BasicChild
    assert get_class_from_parent_subclasses("ChildOfChild", Parent) is None
    assert get_class_from_parent_subclasses("ChildOfChild", BasicChild) is ChildOfChild
    assert get_class_from_parent_subclasses("BasicChild", ChildOfChild) is None


def test_get_deep_class_from_parent_subclasses():
    assert get_deep_class_from_parent_subclasses("BasicChild", Parent) is BasicChild
    assert get_deep_class_from_parent_subclasses("ChildOfChild", Parent) is ChildOfChild
    assert get_deep_class_from_parent_subclasses("ChildOfChild", BasicChild) is ChildOfChild
    assert get_deep_class_from_parent_subclasses("BasicChild", ChildOfChild) is None


def test_is_abstract_using_inspection_and_class_naming():
    assert is_abstract_using_inspection_and_class_naming(AbstractParent)
    assert not is_abstract_using_inspection_and_class_naming(Parent)
    assert not is_abstract_using_inspection_and_class_naming(ChildOfChild)


def test_get_all_classes_from_parent():
    assert get_all_classes_from_parent(Parent) == [BasicChild, ChildOfChild]
    assert get_all_classes_from_parent(BasicChild) == [ChildOfChild]
    assert get_all_classes_from_parent(ChildOfChild) == []


def test_get_single_deepest_child_class():
    assert get_single_deepest_child_class(Parent) == ChildOfChild
    assert get_single_deepest_child_class(BasicChild) == ChildOfChild
    assert get_single_deepest_child_class(ChildOfChild) == ChildOfChild
