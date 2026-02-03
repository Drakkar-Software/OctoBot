#  Drakkar-Software OctoBot-Tentacles
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
import pytest_asyncio


import tests.functional_tests.evaluators_tests.abstract_TA_test as abstract_TA_test
import tentacles.Evaluator.TA as TA


# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def evaluator_tester():
    evaluator_tester_instance = TestKlingerEvaluator()
    evaluator_tester_instance.TA_evaluator_class = TA.KlingerOscillatorMomentumEvaluator
    return evaluator_tester_instance


class TestKlingerEvaluator(abstract_TA_test.AbstractTATest):

    @staticmethod
    async def test_stress_test(evaluator_tester):
        await evaluator_tester.run_stress_test_without_exceptions(0.7, False, skip_long_time_frames=True)

    @staticmethod
    async def test_reactions_to_dump(evaluator_tester):
        await evaluator_tester.run_test_reactions_to_dump(0, 0, -0.2, -0.4, -0.55)

    @staticmethod
    async def test_reactions_to_pump(evaluator_tester):
        await evaluator_tester.run_test_reactions_to_pump(-0.1, -0.1, 0, 0.1, 0.2,
                                                          0, -0.5)

    @staticmethod
    async def test_reaction_to_rise_after_over_sold(evaluator_tester):
        await evaluator_tester.run_test_reactions_to_rise_after_over_sold(-0.2, -0.6, -1, -1, 0.1)

    @staticmethod
    async def test_reaction_to_over_bought_then_dip(evaluator_tester):
        await evaluator_tester.run_test_reactions_to_over_bought_then_dip(-1, 0, 0.5, 0.5, -0.8, -1)

    @staticmethod
    async def test_reaction_to_flat_trend(evaluator_tester):
        await evaluator_tester.run_test_reactions_to_flat_trend(
            # eval_start_move_ending_up_in_a_rise,
            0.9,
            # eval_reaches_flat_trend, eval_first_micro_up_p1, eval_first_micro_up_p2,
            0.7, 0.55, 0.3,
            # eval_micro_down1, eval_micro_up1, eval_micro_down2, eval_micro_up2,
            -0.3, -0.25, -0.4, -0.1,
            # eval_micro_down3, eval_back_normal3, eval_micro_down4, eval_back_normal4,
            0, -0.1, 0.1, 0.1,
            # eval_micro_down5, eval_back_up5, eval_micro_up6, eval_back_down6,
            -0.1, -0.1, 0.1, 0.25,
            # eval_back_normal6, eval_micro_down7, eval_back_up7, eval_micro_down8,
            0, 0.1, -0.2, 0,
            # eval_back_up8, eval_micro_down9, eval_back_up9
            0, 0, 0.1)
