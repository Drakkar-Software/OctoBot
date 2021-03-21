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

cimport octobot.backtesting as octobot_backtesting
cimport octobot.strategy_optimizer as strategy_optimizer


cdef class StrategyTestSuite(octobot_backtesting.AbstractBacktestingTest):
    cdef list _profitability_results
    cdef list _trades_counts

    cdef public double current_progress
    cdef public list exceptions
    cdef public list evaluators

    cpdef strategy_optimizer.TestSuiteResult get_test_suite_result(self)
