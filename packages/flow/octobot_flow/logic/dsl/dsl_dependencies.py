import octobot_trading.dsl
import octobot_commons.enums
import octobot_commons.dsl_interpreter
import octobot_flow.entities
import octobot_flow.logic.dsl.dsl_executor as dsl_executor
import octobot_commons.profiles.profile_data as profile_data_import


def get_actions_symbol_dependencies(
    actions: list[octobot_flow.entities.AbstractActionDetails],
    minimal_profile_data: profile_data_import.ProfileData
) -> list[str]:
    all_symbol_dependencies = [
        _get_symbol_dependencies(minimal_profile_data, action.get_resolved_dsl_script())
        for action in actions
        if isinstance(action, octobot_flow.entities.DSLScriptActionDetails)
    ]
    return list(set(
        symbol_dependency.symbol
        for symbol_dependencies in all_symbol_dependencies 
        for symbol_dependency in symbol_dependencies
    ))


def get_actions_time_frames_dependencies(
    actions: list[octobot_flow.entities.AbstractActionDetails],
    minimal_profile_data: profile_data_import.ProfileData
) -> list[octobot_commons.enums.TimeFrames]:
    all_symbol_dependencies = [
        _get_symbol_dependencies(minimal_profile_data, action.get_resolved_dsl_script())
        for action in actions
        if isinstance(action, octobot_flow.entities.DSLScriptActionDetails)
    ]
    return list(set(
        octobot_commons.enums.TimeFrames(symbol_dependency.time_frame)
        for symbol_dependencies in all_symbol_dependencies 
        for symbol_dependency in symbol_dependencies
        if symbol_dependency.time_frame
    ))


def get_copy_trading_dependencies(
    actions: list[octobot_flow.entities.AbstractActionDetails],
    minimal_profile_data: profile_data_import.ProfileData,
) -> list[octobot_trading.dsl.CopyTradingDependency]:
    all_copy_trading_dependencies = [
        _get_copy_trading_dependencies(minimal_profile_data, action.get_resolved_dsl_script())
        for action in actions
        if isinstance(action, octobot_flow.entities.DSLScriptActionDetails)
    ]
    return list(set(
        copy_trading_dependency
        for copy_trading_dependencies in all_copy_trading_dependencies
        for copy_trading_dependency in copy_trading_dependencies
    ))


def _get_symbol_dependencies(
    minimal_profile_data: profile_data_import.ProfileData,
    dsl_script: str
) -> list[octobot_trading.dsl.SymbolDependency]:
    return [
        symbol_dependency
        for symbol_dependency in get_dsl_dependencies(minimal_profile_data, dsl_script)
        if isinstance(symbol_dependency, octobot_trading.dsl.SymbolDependency)
    ]


def _get_copy_trading_dependencies(
    minimal_profile_data: profile_data_import.ProfileData,
    dsl_script: str
) -> list[octobot_trading.dsl.CopyTradingDependency]:
    return [
        copy_trading_dependency
        for copy_trading_dependency in get_dsl_dependencies(minimal_profile_data, dsl_script)
        if isinstance(copy_trading_dependency, octobot_trading.dsl.CopyTradingDependency)
    ]

def get_dsl_dependencies(
    minimal_profile_data: profile_data_import.ProfileData,
    dsl_script: str
) -> list[octobot_commons.dsl_interpreter.InterpreterDependency]:
    dependencies_only_executor = dsl_executor.DSLExecutor(
        minimal_profile_data, None, dsl_script
    )
    return dependencies_only_executor.get_dependencies()
