import { describe, it, expect } from "vitest";
import {
  sendActionsToAutomation,
  triggerCopierAutomation,
  sendForcedTriggerToAutomation,
} from "../src/dispatch.js";
import { AutomationWorkflowActionType } from "../src/enums.js";
import { TaskStatus } from "@drakkarsoftware/octobot-protocol";
import type { Action } from "@drakkarsoftware/octobot-protocol";

const action = (id: string): Action => ({
  id,
  actionType: "test",
  status: TaskStatus.Pending,
});

describe("dispatch helpers", () => {
  it("sendActionsToAutomation produces a USER_ACTIONS envelope", () => {
    const actions = [action("a1")];
    const env = sendActionsToAutomation("auto1", actions);
    expect(env.automationId).toBe("auto1");
    expect(env.actionsType).toBe(AutomationWorkflowActionType.UserActions);
    expect(env.actionsType).toBe("user_actions");
    if (env.actionsType === AutomationWorkflowActionType.UserActions) {
      expect(env.userActions).toBe(actions);
    }
  });

  it("triggerCopierAutomation produces a TRADING_SIGNAL envelope", () => {
    const signals = [{ type: "buy" }];
    const env = triggerCopierAutomation("auto1", signals);
    expect(env.automationId).toBe("auto1");
    expect(env.actionsType).toBe(AutomationWorkflowActionType.TradingSignal);
    expect(env.actionsType).toBe("trading_signal");
    if (env.actionsType === AutomationWorkflowActionType.TradingSignal) {
      expect(env.tradingSignals).toBe(signals);
    }
  });

  it("sendForcedTriggerToAutomation produces a FORCED_TRIGGER envelope", () => {
    const env = sendForcedTriggerToAutomation("auto1");
    expect(env.automationId).toBe("auto1");
    expect(env.actionsType).toBe(AutomationWorkflowActionType.ForcedTrigger);
    expect(env.actionsType).toBe("forced_trigger");
  });
});
