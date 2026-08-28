import octobot_node.scheduler.automations.automation_states_loader as automations_automation_states_loader
import octobot_node.scheduler.automations.generic_process_octobot as automations_generic_process_octobot
import octobot_node.scheduler.automations.octobot_flow_client as automations_octobot_flow_client
import octobot_node.scheduler.automations.trade_symbols_resolver as automations_trade_symbols_resolver

STATE_KEY = automations_automation_states_loader.STATE_KEY
create_generic_process_bot = automations_generic_process_octobot.create_generic_process_bot
get_automation_copied_strategy_ids = automations_automation_states_loader.get_automation_copied_strategy_ids
get_automation_dict = automations_automation_states_loader.get_automation_dict
get_automation_id = automations_automation_states_loader.get_automation_id
get_automation_state_dict = automations_automation_states_loader.get_automation_state_dict
get_automation_state_reader = automations_automation_states_loader.get_automation_state_reader
get_automation_workflow_status = automations_automation_states_loader.get_automation_workflow_status
load_flow_automation_states_by_id = automations_automation_states_loader.load_flow_automation_states_by_id
load_protocol_automation_states = automations_automation_states_loader.load_protocol_automation_states
load_wallet_automation_states = automations_automation_states_loader.load_wallet_automation_states
load_wallet_automation_states_for_trade_symbols = (
    automations_automation_states_loader.load_wallet_automation_states_for_trade_symbols
)
parse_flow_automation_state = automations_automation_states_loader.parse_flow_automation_state
patch_task_content_degraded_state = automations_automation_states_loader.patch_task_content_degraded_state
resolve_trade_symbols = automations_trade_symbols_resolver.resolve_trade_symbols
OctoBotActionsJob = automations_octobot_flow_client.OctoBotActionsJob
OctoBotActionsJobDescription = automations_octobot_flow_client.OctoBotActionsJobDescription
OctoBotActionsJobResult = automations_octobot_flow_client.OctoBotActionsJobResult

__all__ = [
    "OctoBotActionsJob",
    "OctoBotActionsJobDescription",
    "OctoBotActionsJobResult",
    "STATE_KEY",
    "create_generic_process_bot",
    "get_automation_copied_strategy_ids",
    "get_automation_dict",
    "get_automation_id",
    "get_automation_state_dict",
    "get_automation_state_reader",
    "get_automation_workflow_status",
    "load_flow_automation_states_by_id",
    "load_protocol_automation_states",
    "load_wallet_automation_states",
    "load_wallet_automation_states_for_trade_symbols",
    "parse_flow_automation_state",
    "patch_task_content_degraded_state",
    "resolve_trade_symbols",
]
