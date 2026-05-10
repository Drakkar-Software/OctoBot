import type { ActionHandler } from "../../actions.js";
import { addAutomationHandler } from "./addAutomation.js";
import { addExchangeAccountHandler } from "./addExchangeAccount.js";
import { removeAutomationHandler } from "./removeAutomation.js";
import { removeExchangeAccountHandler } from "./removeExchangeAccount.js";

export {
  addAutomationHandler,
  addExchangeAccountHandler,
  removeAutomationHandler,
  removeExchangeAccountHandler,
};

export const defaultActionHandlers: Record<string, ActionHandler> = {
  add_exchange_account: addExchangeAccountHandler,
  remove_exchange_account: removeExchangeAccountHandler,
  add_automation: addAutomationHandler,
  remove_automation: removeAutomationHandler,
};
