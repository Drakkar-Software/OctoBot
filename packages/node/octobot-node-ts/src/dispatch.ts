import type { Action } from "@drakkarsoftware/octobot-protocol";
import { AutomationWorkflowActionType } from "./enums.js";
import type { AutomationWorkflowActionUpdate } from "./envelope.js";

export function sendActionsToAutomation(
  automationId: string,
  actions: Action[],
): AutomationWorkflowActionUpdate {
  return {
    automationId,
    actionsType: AutomationWorkflowActionType.UserActions,
    userActions: actions,
  };
}

export function triggerCopierAutomation(
  automationId: string,
  tradingSignals: unknown[],
): AutomationWorkflowActionUpdate {
  return {
    automationId,
    actionsType: AutomationWorkflowActionType.TradingSignal,
    tradingSignals,
  };
}

export function sendForcedTriggerToAutomation(
  automationId: string,
): AutomationWorkflowActionUpdate {
  return {
    automationId,
    actionsType: AutomationWorkflowActionType.ForcedTrigger,
  };
}
