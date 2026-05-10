import type { Action, AutomationsState, RemoveExchangeAccountAction } from "@drakkarsoftware/octobot-protocol";
import type { ExchangeManager } from "@drakkarsoftware/octobot-trading";
import type { AutomationContext } from "../../../runner.js";

export function createRemoveExchangeAccountHandler(registry: Map<string, ExchangeManager>) {
  return async function removeExchangeAccountHandler(
    action: Action,
    ctx: AutomationContext,
    _state: AutomationsState,
  ): Promise<unknown> {
    const { accountId } = action as RemoveExchangeAccountAction;

    const manager = registry.get(accountId);
    if (manager) {
      await manager.stop();
      registry.delete(accountId);
    }

    ctx.removeAccount?.(accountId);
    return { accountId };
  };
}
