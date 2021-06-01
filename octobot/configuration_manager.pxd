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


cdef class ConfigurationManager:
    cdef dict configuration_elements

    cpdef void add_element(self, str key, object element, bint has_dict=*)
    cpdef object get_edited_config(self, str key, bint dict_only)
    cpdef object get_startup_config(self, str key, bint dict_only)
    cpdef void set_edited_config(self, str config_key, object config)

cdef class ConfigurationElement:
    cdef public object config
    cdef public bint has_dict
    cdef public object startup_config
    cdef public object edited_config

cpdef config_health_check(object config, bint in_backtesting)
cpdef str get_default_tentacles_url(str version=*)
cpdef str get_default_compiled_tentacles_url()
cpdef str get_user_local_config_file()
cpdef void set_default_profile(object config, str from_default_config_file=*)
