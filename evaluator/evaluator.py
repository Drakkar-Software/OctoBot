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

from evaluator.evaluator_creator import EvaluatorCreator


class Evaluator:
    def __init__(self):
        self.config = None
        self.symbol = None
        self.time_frame = None
        self.history_time = None
        self.data = None
        self.symbol = None
        self.exchange = None
        self.symbol_evaluator = None
        self.data_changed = False

        self.social_eval_list = []
        self.ta_eval_list = []
        self.real_time_eval_list = []

        self.creator = EvaluatorCreator()

    def set_data(self, data):
        self.data = data
        self.data_changed = True

    def set_time_frame(self, time_frame):
        self.time_frame = time_frame
        if time_frame is not None:
            self.history_time = time_frame.value

    def set_ta_eval_list(self, new_ta_list, evaluation_consumer):
        self.ta_eval_list = new_ta_list
        for ta_eval in self.ta_eval_list:
            evaluation_consumer.symbol_evaluator \
                .add_evaluator_instance_to_strategy_instances_list(ta_eval, evaluation_consumer.exchange)

    def set_social_eval(self, new_social_list, evaluation_consumer):
        self.social_eval_list = new_social_list
        for social_eval in self.social_eval_list:
            social_eval.add_evaluation_consumer(evaluation_consumer)
            evaluation_consumer.symbol_evaluator \
                .add_evaluator_instance_to_strategy_instances_list(social_eval, evaluation_consumer.exchange)

    def set_real_time_eval(self, new_real_time_list, evaluation_consumer):
        self.real_time_eval_list = new_real_time_list
        for real_time_eval in self.real_time_eval_list:
            evaluation_consumer.symbol_evaluator \
                .add_evaluator_instance_to_strategy_instances_list(real_time_eval, evaluation_consumer.exchange)

    async def update_ta_eval(self, ignored_evaluator=None):
        # update only with new data
        if self.data_changed:
            for ta_evaluator in self.ta_eval_list:
                ta_evaluator.set_data(self.data)
                if not ta_evaluator.get_name() == ignored_evaluator and ta_evaluator.get_is_evaluable():
                    await ta_evaluator.eval()

            # reset data changed after update
            self.data_changed = False
