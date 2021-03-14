# cython: language_level=3
#  Drakkar-Software OctoBot-Backtesting
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

cdef class AbstractBacktestingTest:
    cdef dict config
    cdef object tentacles_setup_config
    cdef object strategy_evaluator_class
    cdef object logger

    cpdef void initialize_with_strategy(self,
                                        object strategy_evaluator_class,
                                        object tentacles_setup_config,
                                        dict config)

    cdef void _register_only_strategy(self, object strategy_evaluator_class)
