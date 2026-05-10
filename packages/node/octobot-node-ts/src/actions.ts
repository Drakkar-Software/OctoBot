import type { Action, AutomationsState, Execution } from "@drakkarsoftware/octobot-protocol";
import { TaskStatus } from "@drakkarsoftware/octobot-protocol";
import type { Automation, AutomationContext } from "./runner.js";
import { ActionHandlerNotFoundError } from "./errors.js";

export type ActionHandler = (
  action: Action,
  ctx: AutomationContext,
  state: AutomationsState,
) => Promise<unknown>;

export function assertHandlerExists(
  actionType: string,
  handlers: Record<string, ActionHandler> | undefined,
): ActionHandler {
  const handler = handlers?.[actionType];
  if (!handler) throw new ActionHandlerNotFoundError(actionType);
  return handler;
}

export function actionToAutomation(
  action: Action,
  handler: ActionHandler,
): Automation<AutomationsState, unknown> {
  return {
    id: action.id,
    metadata: { name: action.actionType, description: "" },
    run: (ctx: AutomationContext, state: AutomationsState) => handler(action, ctx, state),
  };
}

export function applyExecutionToAction(action: Action, exec: Execution): Action {
  const base: Action = { ...action, status: exec.status };
  if (exec.status === TaskStatus.Completed) {
    return {
      ...base,
      completedAt: exec.completedAt !== undefined ? new Date(exec.completedAt) : undefined,
      result: exec.result !== undefined ? JSON.stringify(exec.result) : undefined,
      error: undefined,
    };
  }
  if (exec.status === TaskStatus.Failed) {
    return {
      ...base,
      completedAt: exec.completedAt !== undefined ? new Date(exec.completedAt) : undefined,
      error: exec.error?.message,
      result: undefined,
    };
  }
  if (exec.status === TaskStatus.Cancelled) {
    return {
      ...base,
      completedAt: exec.completedAt !== undefined ? new Date(exec.completedAt) : undefined,
    };
  }
  return base;
}
