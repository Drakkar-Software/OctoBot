import type { ExchangeManager } from "@drakkarsoftware/octobot-trading";
import type { ActionHandler } from "../../../actions.js";
import { createAddExchangeAccountHandler } from "./addExchangeAccount.js";
import { createRemoveExchangeAccountHandler } from "./removeExchangeAccount.js";

export { createAddExchangeAccountHandler, createRemoveExchangeAccountHandler };

export function createTradingHandlers(registry: Map<string, ExchangeManager>): Record<string, ActionHandler> {
  return {
    add_exchange_account: createAddExchangeAccountHandler(registry),
    remove_exchange_account: createRemoveExchangeAccountHandler(registry),
  };
}
