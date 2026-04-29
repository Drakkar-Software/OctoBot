# pylint: disable=C0116
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
import typing

import octobot_commons.enums


class SignalDependencies:
    def __init__(self, dependencies: typing.Optional[list[dict]] = None):
        self.dependencies: list[dict] = dependencies if dependencies else []

    def extend(self, dependencies: "SignalDependencies"):
        self.dependencies.extend(dependencies.dependencies)

    def is_filled_by(self, filled_dependencies: "SignalDependencies") -> bool:
        for dependency in self.dependencies:
            has_missing_dependency = True
            for filled_dependency in filled_dependencies.dependencies:
                has_missing_dependency = bool(
                    {
                        key: value
                        for key, value in dependency.items()
                        if key not in filled_dependency
                        or filled_dependency[key] != value
                    }
                )
                if not has_missing_dependency:
                    break
            # iterated over all filled_dependency and did not break,
            # this dependency is not filled
            if has_missing_dependency:
                return False
        # all dependencies are filled
        return True

    def to_dict(self) -> dict:
        return {
            octobot_commons.enums.SignalDependenciesAttrs.DEPENDENCY.value: self.dependencies,
        }

    def __str__(self):
        return f"{self.to_dict()}"

    def __repr__(self):
        return self.__str__()

    def __eq__(self, other: "SignalDependencies") -> bool:
        if self is other:
            return True
        if not isinstance(other, SignalDependencies):
            return False
        return self.dependencies == other.dependencies

    def __bool__(self) -> bool:
        return bool(self.dependencies)
