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


cdef class TestSuiteResult:
    cdef public list run_profitabilities
    cdef public list trades_counts
    cdef public double risk
    cdef public list time_frames
    cdef public object min_time_frame
    cdef public list evaluators
    cdef public str strategy

    cpdef double get_average_score(self)
    cpdef double get_average_trades_count(self)
    cpdef list get_evaluators_without_strategy(self)
    cpdef TestSuiteResultSummary get_config_summary(self)
    cpdef str get_result_string(self, bint details=*)
    cpdef dict get_result_dict(self, int index=*)

cdef class TestSuiteResultSummary:
    cdef public list evaluators
    cdef public double risk

    cpdef str get_result_string(self)
