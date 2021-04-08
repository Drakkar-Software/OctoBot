# cython: language_level=3
#  Drakkar-Software OctoBot
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

cimport octobot.updater.updater as updater_class

cdef class PythonUpdater(updater_class.Updater):
    cdef bint use_git

    cdef str _get_latest_pypi_release_url(self)
    cdef object _get_latest_pypi_version_from_data(self, object pypi_package_data)
    cdef object _run_git_get_latest_tag(self)
    cdef object _run_git_get_last_tag_hash(self)
    cdef object _run_git_remove_local_branch(self, str branch_name)
    cdef object _run_pip_install_package(self, str package_name)
    cdef object _run_pip_update_package(self, str package_name)
    cdef object _run_pip_install_requirements_file(self, str requirement_file)
