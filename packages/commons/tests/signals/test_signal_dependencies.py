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
import pytest
import copy

import octobot_commons.enums
import octobot_commons.signals as signals


@pytest.fixture
def no_dependencies():
    return signals.SignalDependencies()


@pytest.fixture
def single_dependencies():
    return signals.SignalDependencies([
        {"PLIP": "123"}
    ])


@pytest.fixture
def dual_dependencies():
    return signals.SignalDependencies([
        {"plop": "123"},
        {"PLIP": "123"}
    ])


def test_extend(no_dependencies, single_dependencies, dual_dependencies):
    no_dependencies.extend(no_dependencies)
    assert no_dependencies == no_dependencies
    no_dependencies.extend(single_dependencies)
    assert no_dependencies == single_dependencies
    single_dependencies.extend(dual_dependencies)
    assert single_dependencies == signals.SignalDependencies([
        {"PLIP": "123"},
        {"plop": "123"},
        {"PLIP": "123"}
    ])


def test_is_filled_by(no_dependencies, single_dependencies, dual_dependencies):
    assert no_dependencies.is_filled_by(no_dependencies) is True
    assert no_dependencies.is_filled_by(single_dependencies) is True
    assert no_dependencies.is_filled_by(dual_dependencies) is True


    assert single_dependencies.is_filled_by(no_dependencies) is False
    assert single_dependencies.is_filled_by(single_dependencies) is True
    assert single_dependencies.is_filled_by(dual_dependencies) is True

    assert dual_dependencies.is_filled_by(no_dependencies) is False
    assert dual_dependencies.is_filled_by(single_dependencies) is False
    assert dual_dependencies.is_filled_by(dual_dependencies) is True

    # with extended dependencies
    saved_no_dependencies = copy.deepcopy(no_dependencies)
    no_dependencies.extend(single_dependencies)
    assert no_dependencies.is_filled_by(saved_no_dependencies) is False
    assert no_dependencies.is_filled_by(single_dependencies) is True
    assert no_dependencies.is_filled_by(dual_dependencies) is True


def test_to_dict(no_dependencies, single_dependencies, dual_dependencies):
    assert no_dependencies.to_dict() == {
        octobot_commons.enums.SignalDependenciesAttrs.DEPENDENCY.value: []
    }
    assert single_dependencies.to_dict() == {
        octobot_commons.enums.SignalDependenciesAttrs.DEPENDENCY.value: [
            {"PLIP": "123"}
        ]
    }
    assert dual_dependencies.to_dict() == {
        octobot_commons.enums.SignalDependenciesAttrs.DEPENDENCY.value: [
            {"plop": "123"},
            {"PLIP": "123"}
        ]
    }


def test_eq(no_dependencies, single_dependencies, dual_dependencies):
    assert no_dependencies != None
    assert no_dependencies == no_dependencies
    assert no_dependencies == signals.SignalDependencies()
    assert single_dependencies == single_dependencies
    assert single_dependencies == signals.SignalDependencies([
        {"PLIP": "123"}
    ])
    assert dual_dependencies == dual_dependencies
    assert dual_dependencies == signals.SignalDependencies([
        {"plop": "123"},
        {"PLIP": "123"}
    ])
    assert no_dependencies != single_dependencies


def test_bool(no_dependencies, single_dependencies, dual_dependencies):
    assert bool(no_dependencies) is False
    assert bool(single_dependencies) is True
    assert bool(dual_dependencies) is True
