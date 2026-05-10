// Public API.
export * from "./errors.js";
export * from "./enums.js";
export * from "./envelope.js";
export * from "./dispatch.js";
export * from "./execution.js";
export * from "./state.js";
export * from "./runner.js";
export * from "./actions.js";
export * from "./accounts.js";
export * from "./workflow.js";
export * from "./node.js";
export * from "./actions/handlers/index.js";

export { newId } from "./util/id.js";
export { now, setNowForTesting, resetNow } from "./util/time.js";

// Re-export protocol types consumers will reach for.
export type {
  AutomationsState,
  AutomationState,
  AutomationMetadata,
  AccountsState,
  Account,
  ExchangeAccount,
  BlockchainAccount,
  Asset,
  Action,
  ActionBase,
  AddExchangeAccountAction,
  RemoveExchangeAccountAction,
  AddAutomationAction,
  RemoveAutomationAction,
  Execution,
  ExecutionError,
  TaskStatus,
} from "@drakkarsoftware/octobot-protocol";

export { TaskStatus as TaskStatusValues } from "@drakkarsoftware/octobot-protocol";
