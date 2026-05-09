// Public API.
export * from "./errors.js";
export * from "./automation.js";
export * from "./execution.js";
export * from "./state.js";
export * from "./runner.js";
export * from "./node.js";

export { newId } from "./util/id.js";
export { now, setNowForTesting, resetNow } from "./util/time.js";

// Re-export the protocol types most consumers will reach for.
export type {
  AutomationsState,
  AutomationState,
  AutomationMetadata,
  Execution,
  ExecutionError,
  TaskStatus,
} from "@drakkarsoftware/octobot-protocol";
