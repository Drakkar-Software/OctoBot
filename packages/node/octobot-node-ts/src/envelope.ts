import type { Action } from "@drakkarsoftware/octobot-protocol";
import { AutomationWorkflowActionType } from "./enums.js";

export type AutomationWorkflowActionUpdate =
  | {
      automationId: string;
      actionsType: typeof AutomationWorkflowActionType.UserActions;
      userActions: Action[];
    }
  | {
      automationId: string;
      actionsType: typeof AutomationWorkflowActionType.TradingSignal;
      tradingSignals: unknown[];
    }
  | {
      automationId: string;
      actionsType: typeof AutomationWorkflowActionType.ForcedTrigger;
    };
