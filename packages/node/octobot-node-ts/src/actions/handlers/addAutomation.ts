import type { Action, AddAutomationAction, AutomationsState } from "@drakkarsoftware/octobot-protocol";
import type { AutomationContext } from "../../runner.js";

export async function addAutomationHandler(
  action: Action,
  ctx: AutomationContext,
  _state: AutomationsState,
): Promise<unknown> {
  const { automation } = action as AddAutomationAction;
  ctx.replaceAutomation?.(automation);
  return automation;
}
