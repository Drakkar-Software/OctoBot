#  Drakkar-Software OctoBot-Tentacles-Manager
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

import fnmatch
import os
import os.path as path
from pathlib import PurePath

import octobot_tentacles_manager.constants as constants
import octobot_tentacles_manager.util.tentacle_explorer as explorer
import octobot_tentacles_manager.util.tentacle_processing as tentacle_processing


def filter_tentacles_by_dev_mode_and_package(tentacles: list,
                                             with_dev_mode: bool = False,
                                             package_filter: str = None) -> list:
    # remove dev-mode tentacles if necessary
    tentacles_white_list = tentacles if with_dev_mode else _filter_in_dev_tentacles(tentacles)
    if package_filter is not None:
        # only keep tentacles from the tentacles package to export
        tentacles_white_list = explorer.get_tentacles_from_package(tentacles_white_list, package_filter)
    return tentacles_white_list


def _filter_in_dev_tentacles(tentacles):
    return [
        tentacle
        for tentacle in tentacles
        if not tentacle.in_dev_mode
    ]


def should_ignore_by_include(element_path, element_name, tentacle_root, include_patterns):
    if element_name in constants.ALWAYS_INCLUDED_TENTACLE_FILES:
        return False

    rel_dir = path.relpath(element_path, tentacle_root)
    rel_path = element_name if rel_dir == "." else path.join(rel_dir, element_name)
    rel_path = rel_path.replace(os.sep, '/')

    if path.isdir(path.join(element_path, element_name)):
        return not any(
            tentacle_processing.could_match_under_dir(rel_path, pattern)
            for pattern in include_patterns
        )
    else:
        return not any(
            tentacle_processing.matches_pattern(rel_path, pattern)
            for pattern in include_patterns
        )


def should_include_ignore_function(tentacle_root, include_patterns):
    def _ignore(folder_path, names):
        return {
            name for name in names
            if should_ignore_by_include(folder_path, name, tentacle_root, include_patterns)
        }
    return _ignore


class TentacleFilter:
    def __init__(self, full_tentacles_list, tentacles_white_list):
        self.tentacles_white_list = tentacles_white_list
        self.full_tentacles_list = full_tentacles_list
        self.tentacle_paths_black_list = [] if self.tentacles_white_list is None else [
            path.join(tentacle.tentacle_path, tentacle.name)
            for tentacle in self.full_tentacles_list
            if tentacle not in self.tentacles_white_list
        ]
        self.ignored_elements = constants.TENTACLES_PACKAGE_IGNORED_ELEMENTS
        # Build mapping: tentacle_module_path -> include_patterns
        self.tentacle_include_map = {}
        if self.tentacles_white_list:
            for tentacle in self.tentacles_white_list:
                if tentacle.include_patterns:
                    self.tentacle_include_map[tentacle.tentacle_module_path] = tentacle.include_patterns

    def should_ignore(self, folder_path, names):
        return [name
                for name in names
                if self._should_ignore(folder_path, name)]

    def _should_ignore(self, element_path, element_name):
        if element_name in self.ignored_elements:
            return True
        if self.tentacles_white_list is not None:
            candidate_path = path.join(element_path, element_name)
            if path.isdir(candidate_path) and candidate_path in self.tentacle_paths_black_list:
                return True
        
        # Check if we're inside a tentacle with include patterns
        # by checking if any tentacle_module_path is a parent of element_path
        for tentacle_path, include_patterns in self.tentacle_include_map.items():
            if self._is_path_inside_tentacle(element_path, tentacle_path):
                return should_ignore_by_include(
                    element_path, element_name, tentacle_path, include_patterns
                )
        return False

    @staticmethod
    def _is_path_inside_tentacle(element_path, tentacle_path):
        try:
            # Get the relative path; if it doesn't start with .., then it's inside
            rel = path.relpath(element_path, tentacle_path)
            return not rel.startswith('..')
        except ValueError:
            # Different drives on Windows
            return False

