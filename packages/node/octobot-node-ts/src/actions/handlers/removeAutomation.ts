import type { Action, AutomationsState, RemoveAutomationAction } from "@drakkarsoftware/octobot-protocol";
import type { AutomationContext } from "../../runner.js";

export async function removeAutomationHandler(
  action: Action,
  ctx: AutomationContext,
  _state: AutomationsState,
): Promise<unknown> {
  const { automationId } = action as RemoveAutomationAction;
  ctx.removeAutomation?.(automationId);
  return { automationId };
}
