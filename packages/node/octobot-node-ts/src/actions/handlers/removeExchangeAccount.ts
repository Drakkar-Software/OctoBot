import type { Action, AutomationsState, RemoveExchangeAccountAction } from "@drakkarsoftware/octobot-protocol";
import type { AutomationContext } from "../../runner.js";

export async function removeExchangeAccountHandler(
  action: Action,
  ctx: AutomationContext,
  _state: AutomationsState,
): Promise<unknown> {
  const { accountId } = action as RemoveExchangeAccountAction;
  ctx.removeAccount?.(accountId);
  return { accountId };
}
