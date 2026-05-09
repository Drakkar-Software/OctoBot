import type { Execution, ExecutionError, TaskStatus } from "@drakkarsoftware/octobot-protocol";
import { TaskStatus as TaskStatusValues } from "@drakkarsoftware/octobot-protocol";
import { newId } from "./util/id.js";
import { now } from "./util/time.js";

export const ExecutionStatus = TaskStatusValues;
export type ExecutionStatus = TaskStatus;

export function newExecution(args: {
  automationId: string;
  reason: string;
  input?: unknown;
}): Execution {
  return {
    id: newId(),
    automationId: args.automationId,
    reason: args.reason,
    startedAt: now(),
    status: TaskStatusValues.Pending,
    input: args.input as { [key: string]: unknown } | undefined,
  };
}

export function markRunning(execution: Execution): Execution {
  return { ...execution, status: TaskStatusValues.Running };
}

export function markSuccess(execution: Execution, result: unknown): Execution {
  return {
    ...execution,
    status: TaskStatusValues.Completed,
    completedAt: now(),
    result: result as { [key: string]: unknown } | undefined,
  };
}

export function markFailed(execution: Execution, error: unknown): Execution {
  return {
    ...execution,
    status: TaskStatusValues.Failed,
    completedAt: now(),
    error: serializeError(error),
  };
}

export function markCancelled(execution: Execution): Execution {
  return {
    ...execution,
    status: TaskStatusValues.Cancelled,
    completedAt: now(),
  };
}

export function serializeError(err: unknown): ExecutionError {
  if (err instanceof Error) {
    return { name: err.name, message: err.message, stack: err.stack };
  }
  return { message: typeof err === "string" ? err : JSON.stringify(err) };
}

export function isTerminal(status: TaskStatus): boolean {
  return (
    status === TaskStatusValues.Completed ||
    status === TaskStatusValues.Failed ||
    status === TaskStatusValues.Cancelled
  );
}
