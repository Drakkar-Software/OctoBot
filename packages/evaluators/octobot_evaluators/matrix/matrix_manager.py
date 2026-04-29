#  Drakkar-Software OctoBot-Evaluators
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
import time
import typing

import octobot_commons.constants as common_constants
import octobot_commons.enums as common_enums
import octobot_commons.evaluators_util as evaluators_util
import octobot_commons.logging as logging

import octobot_evaluators.enums as enums
import octobot_evaluators.constants as constants
import octobot_evaluators.errors as errors
import octobot_evaluators.matrix as matrix


def get_matrix(matrix_id: str) -> matrix.Matrix:
    """
    Get the matrix from its id
    :param matrix_id: the matrix id
    :return: the matrix instance
    """
    return matrix.Matrices.instance().get_matrix(matrix_id)


def set_tentacle_value(matrix_id: str, tentacle_path, tentacle_type, tentacle_value, timestamp=0,
                       description=None, metadata=None):
    """
    Set the node value at tentacle path
    :param matrix_id: the matrix id
    :param tentacle_path: the tentacle path
    :param tentacle_type: the tentacle type
    :param tentacle_value: the tentacle value
    :param timestamp: the value modification timestamp.
    :param description: the tentacle description
    :param metadata: the tentacle metadata
    """
    get_matrix(matrix_id).set_node_value(value=tentacle_value, value_type=tentacle_type,
                                         value_path=tentacle_path, timestamp=timestamp,
                                         description=description, metadata=metadata)


def get_tentacle_node(matrix_id: str, tentacle_path):
    """
    Return the node at tentacle path
    :param matrix_id: the matrix id
    :param tentacle_path: the tentacle path
    :return: the tentacle node
    """
    return get_matrix(matrix_id).get_node_at_path(node_path=tentacle_path)


def delete_tentacle_node(matrix_id, tentacle_path):
    """
    Delete the node at tentacle path
    :param matrix_id: the matrix id
    :param tentacle_path: the tentacle path
    :return: the deleted node
    """
    return get_matrix(matrix_id).delete_node_at_path(node_path=tentacle_path)


def get_tentacle_value(matrix_id: str, tentacle_path) -> typing.Any:
    """
    Get the value of the node at tentacle path
    :param matrix_id: the matrix id
    :param tentacle_path: the tentacle path
    :return: the tentacle value
    """
    tentacle_node = get_tentacle_node(matrix_id, tentacle_path)
    if tentacle_node:
        return tentacle_node.node_value
    return None


def get_tentacle_eval_time(matrix_id: str, tentacle_path) -> typing.Optional[float]:
    """
    Get the evaluation time of the node at tentacle path
    :param matrix_id: the matrix id
    :param tentacle_path: the tentacle path
    :return: the tentacle evaluation time
    """
    tentacle_node = get_tentacle_node(matrix_id, tentacle_path)
    if tentacle_node:
        return tentacle_node.node_value_time
    return None


def get_matrix_default_value_path(tentacle_name: str,
                                  tentacle_type: str,
                                  exchange_name: typing.Optional[str] = None,
                                  cryptocurrency: typing.Optional[str] = None,
                                  symbol: typing.Optional[str] = None,
                                  time_frame: typing.Optional[str] = None) -> list[str]:
    """
    Create matrix value path with default path
    :param tentacle_name:
    :param tentacle_type:
    :param exchange_name:
    :param cryptocurrency:
    :param symbol:
    :param time_frame:
    :return: the default matrix
    """
    return get_tentacle_path(exchange_name=exchange_name,
                             tentacle_type=tentacle_type,
                             tentacle_name=tentacle_name) + get_tentacle_value_path(
        cryptocurrency=cryptocurrency,
        symbol=symbol,
        time_frame=time_frame)


def get_tentacle_nodes(matrix_id, exchange_name=None, tentacle_type=None, tentacle_name=None):
    """
    Returns the list of nodes related to the exchange_name, tentacle_type and tentacle_name, ignored if None
    :param matrix_id: the matrix id
    :param exchange_name: the exchange name to search for in the matrix
    :param tentacle_type: the tentacle type to search for in the matrix
    :param tentacle_name: the tentacle name to search for in the matrix
    :return: nodes linked to the given params
    """
    return get_matrix(matrix_id).get_node_children_at_path(get_tentacle_path(exchange_name=exchange_name,
                                                                             tentacle_type=tentacle_type,
                                                                             tentacle_name=tentacle_name))


def get_node_children_by_names_at_path(matrix_id, node_path, starting_node=None) -> dict:
    """
    :param matrix_id: the matrix id
    :param node_path: the node's path to inspect
    :param starting_node: the node to start the path from, default is the matrix root
    :return: a dict of the children nodes of the given path identified by their name
    """
    return get_matrix(matrix_id).get_node_children_by_names_at_path(node_path, starting_node=starting_node)


def get_tentacles_value_nodes(matrix_id, tentacle_nodes, cryptocurrency=None, symbol=None, time_frame=None):
    """
    Returns the list of nodes related to the symbol and / or time_frame from the given tentacle_nodes list
    :param matrix_id: the matrix id
    :param tentacle_nodes: the exchange name to search for in the matrix
    :param cryptocurrency: the cryptocurrency to search for in the given node list
    :param symbol: the symbol to search for in the given node list
    :param time_frame: the time frame to search for in the given nodes list
    :return: nodes linked to the given params
    """
    return [node_at_path for node_at_path in [
        get_matrix(matrix_id).get_node_at_path(get_tentacle_value_path(cryptocurrency=cryptocurrency,
                                                                       symbol=symbol,
                                                                       time_frame=time_frame),
                                               starting_node=n)
        for n in tentacle_nodes]
            if node_at_path is not None]


def get_latest_eval_time(matrix_id, exchange_name=None, tentacle_type=None, cryptocurrency=None,
                         symbol=None, time_frame=None):
    eval_times = []
    for value_node in matrix.get_tentacles_value_nodes(
            matrix_id,
            get_tentacle_nodes(matrix_id,
                               exchange_name=exchange_name,
                               tentacle_type=tentacle_type),
            cryptocurrency=cryptocurrency,
            symbol=symbol,
            time_frame=time_frame):

        if isinstance(value_node.node_value_time, (float, int)):
            eval_times.append(value_node.node_value_time)
    return max(eval_times) if eval_times else None


def get_tentacle_path(
    exchange_name: typing.Optional[str] = None, 
    tentacle_type: typing.Optional[str] = None, 
    tentacle_name: typing.Optional[str] = None
) -> list[str]:
    """
    Returns the path related to the tentacle name, type and exchange name
    :param tentacle_type: the tentacle type to add in the path, ignored if None
    :param tentacle_name: the tentacle name to add in the path, ignored if None
    :param exchange_name: the exchange name to add in the path (as the first element), ignored if None
    :return: a list of string that represents the path of the given params
    """
    node_path = []
    if exchange_name is not None:
        node_path.append(exchange_name)
    if tentacle_type is not None:
        node_path.append(tentacle_type)
    if tentacle_name is not None:
        node_path.append(tentacle_name)
    return node_path


def get_tentacle_value_path(
    cryptocurrency: typing.Optional[str] = None, 
    symbol: typing.Optional[str] = None, 
    time_frame: typing.Optional[str] = None
) -> list[str]:
    """
    Returns the path related to symbol and / or time_frame values
    :param cryptocurrency: the cryptocurrency to add in the path, ignored if None
    :param symbol: the symbol to add in the path, ignored if None
    :param time_frame: the time frame to add in the path, ignored if None
    :return: a list of string that represents the path of the given params
    """
    node_path: list = []
    if cryptocurrency is not None:
        node_path.append(cryptocurrency)
    if symbol is not None:
        node_path.append(symbol)
    if time_frame is not None:
        node_path.append(time_frame)
    return node_path


def get_evaluations_by_evaluator(matrix_id: str,
                                 exchange_name: typing.Optional[str] = None,
                                 tentacle_type: typing.Optional[str] = None,
                                 cryptocurrency: typing.Optional[str] = None,
                                 symbol: typing.Optional[str] = None,
                                 time_frame: typing.Optional[str] = None,
                                 allow_missing: bool = True,
                                 allowed_values: typing.Optional[list[typing.Any]] = None) -> dict[str, typing.Any]:
    """
    Return a dict of evaluation nodes by evaluator name
    :param matrix_id: the matrix id
    :param exchange_name: the exchange name
    :param tentacle_type: the tentacle type
    :param cryptocurrency: the currency ticker
    :param symbol: the traded pair
    :param time_frame: the evaluation time frame
    :param allow_missing: if False will raise UnsetTentacleEvaluation on missing or invalid evaluation
    :param allowed_values: a white list of allowed values not to be taken as invalid
    :return: the dict of evaluation nodes by evaluator name
    """
    evaluator_nodes = get_node_children_by_names_at_path(matrix_id,
                                                         get_tentacle_path(exchange_name=exchange_name,
                                                                           tentacle_type=tentacle_type))
    evaluations_by_evaluator = {}
    for evaluator_name, node in evaluator_nodes.items():
        evaluation = get_tentacles_value_nodes(matrix_id, [node], cryptocurrency=cryptocurrency,
                                               symbol=symbol, time_frame=time_frame)
        if len(evaluation) > 1:
            logging.get_logger("matrix_manager").warning(
                "More than one evaluation corresponding to the given tentacle filter, "
                "this means there is an issue in this methods given arguments")
        elif evaluation:
            eval_value = evaluation[0].node_value
            if (allowed_values is not None and eval_value in allowed_values) or \
                    evaluators_util.check_valid_eval_note(eval_value):
                evaluations_by_evaluator[evaluator_name] = evaluation[0]
            elif not allow_missing:
                raise errors.UnsetTentacleEvaluation(f"Missing {time_frame if time_frame else 'evaluation'} "
                                                     f"for {evaluator_name} on {symbol}, evaluation is "
                                                     f"{repr(eval_value)}).")
    return evaluations_by_evaluator

def get_evaluation_descriptions_by_evaluator(matrix_id: str, 
    exchange_name: typing.Optional[str] = None, 
    tentacle_type: typing.Optional[str] = None, 
    cryptocurrency: typing.Optional[str] = None, 
    symbol: typing.Optional[str] = None, 
    time_frame: typing.Optional[str] = None,
    allow_missing: bool = True,
    allowed_values: typing.Optional[list[str]] = None
) -> dict[str, str]:
    """
    Return a dict of evaluation descriptions by evaluator name
    :param matrix_id: the matrix id
    :param exchange_name: the exchange name
    :param tentacle_type: the tentacle type
    :param cryptocurrency: the currency ticker
    :param symbol: the traded pair
    :param time_frame: the evaluation time frame
    :return: the dict of evaluation descriptions by evaluator name
    """
    return None # TODO

def get_available_time_frames(matrix_id: str, exchange_name: str, tentacle_type: str, cryptocurrency: str, symbol: str) -> list[str]:
    """
    Return the list of available time frames for the given tentacle
    :param matrix_id: the matrix id
    :param exchange_name: the exchange name
    :param tentacle_type: the tentacle type
    :param cryptocurrency: the currency ticker
    :param symbol: the traded pair
    :return: the list of available time frames for the given tentacle
    """
    try:
        evaluator_nodes = get_node_children_by_names_at_path(matrix_id,
                                                             get_tentacle_path(exchange_name=exchange_name,
                                                                               tentacle_type=tentacle_type))
        first_node = next(iter(evaluator_nodes.values()))
        return list(get_node_children_by_names_at_path(matrix_id,
                                                       get_tentacle_value_path(cryptocurrency=cryptocurrency,
                                                                               symbol=symbol),
                                                       starting_node=first_node))
    except StopIteration:
        return []


def get_available_symbols(matrix_id: str,
                          exchange_name: str,
                          cryptocurrency: str,
                          tentacle_type: typing.Optional[str] = enums.EvaluatorMatrixTypes.TA.value,
                          second_tentacle_type: typing.Optional[str] = enums.EvaluatorMatrixTypes.REAL_TIME.value) -> list[str]:
    """
    Return the list of available symbols for the given currency
    :param matrix_id: the matrix id
    :param exchange_name: the exchange name
    :param cryptocurrency: the cryptocurrency ticker
    :param tentacle_type: the tentacle type to look into first
    :param second_tentacle_type: the tentacle type to look into if no symbol is found in the first tentacle type
    :return: the list of available symbols for the given currency
    """
    try:
        evaluator_nodes = get_node_children_by_names_at_path(matrix_id,
                                                             get_tentacle_path(exchange_name=exchange_name,
                                                                               tentacle_type=tentacle_type))
        first_node = next(iter(evaluator_nodes.values()))
        possible_symbols = list(get_node_children_by_names_at_path(
            matrix_id,
            get_tentacle_value_path(cryptocurrency=cryptocurrency),
            starting_node=first_node))
        if possible_symbols:
            return possible_symbols
        elif tentacle_type != second_tentacle_type:
            # try with second tentacle type
            return get_available_symbols(matrix_id, exchange_name,
                                         cryptocurrency, second_tentacle_type, second_tentacle_type)
    except StopIteration:
        return []


def is_tentacle_value_valid(
    matrix_id: str, tentacle_path, timestamp=0, delta=constants.EVALUATION_ALLOWED_TIME_DELTA
) -> bool:
    """
    Check if the node is ready to be used
    WARNING: This method only works with complete default tentacle path
    :param matrix_id: the matrix id
    :param tentacle_path: the tentacle node path
    :param timestamp: the timestamp to use
    :param delta: the authorized delta to be valid (in seconds)
    :return: True if the node is valid else False
    """
    if timestamp == 0:
        timestamp = time.time()
    try:
        node = get_tentacle_node(matrix_id, tentacle_path)
        if node is None:
            raise KeyError(f"No node at {tentacle_path}")
        return is_evaluation_valid_in_time(
            timestamp,
            node.node_value_time,
            common_enums.TimeFrames(tentacle_path[-1]),
            delta,
        )
    except (IndexError, ValueError):
        return False


def is_evaluation_valid_in_time(
    current_time: float, evaluation_time: float, time_frame: common_enums.TimeFrames,
    allowed_delta=constants.EVALUATION_ALLOWED_TIME_DELTA
):
    """
    :param current_time: the reference current time
    :param evaluation_time: the evaluation time to check
    :param time_frame: the evaluation time frame
    :param allowed_delta: the authorized delta to be valid (in seconds)
    :return: True if the time is valid else False
    """
    return current_time - (
        evaluation_time + common_enums.TimeFramesMinutes[time_frame] * common_constants.MINUTE_TO_SECONDS
        + allowed_delta
    ) < 0


def is_tentacles_values_valid(
    matrix_id: str, tentacle_path_list, timestamp=0, delta=constants.EVALUATION_ALLOWED_TIME_DELTA
) -> bool:
    """
    Check if each of the tentacle path value is valid
    :param matrix_id: the matrix id
    :param tentacle_path_list: the tentacle node path list
    :param timestamp: the timestamp to use
    :param delta: the authorized delta to be valid (in seconds)
    :return: True if all the node values are valid else False
    """
    return all([is_tentacle_value_valid(matrix_id=matrix_id,
                                        tentacle_path=tentacle_path,
                                        timestamp=timestamp,
                                        delta=delta)
                for tentacle_path in tentacle_path_list])
