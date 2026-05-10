import type { Action, AddExchangeAccountAction, AutomationsState } from "@drakkarsoftware/octobot-protocol";
import type { AutomationContext } from "../../runner.js";

export async function addExchangeAccountHandler(
  action: Action,
  ctx: AutomationContext,
  _state: AutomationsState,
): Promise<unknown> {
  const { account } = action as AddExchangeAccountAction;
  ctx.replaceAccount?.(account);
  return account;
}
