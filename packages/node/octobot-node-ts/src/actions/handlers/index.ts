import type { ActionHandler } from "../../actions.js";
import { addAutomationHandler } from "./addAutomation.js";
import { removeAutomationHandler } from "./removeAutomation.js";

export { addAutomationHandler, removeAutomationHandler };

export const defaultActionHandlers: Record<string, ActionHandler> = {
  add_automation: addAutomationHandler,
  remove_automation: removeAutomationHandler,
};
