// Runs a single automation. Owns the status transitions on the Execution
// record (pending → running → terminal) and never throws to the caller — the
// outcome is encoded in the returned Execution.

import { getLogger } from "@drakkarsoftware/octobot-commons";
import type { Execution } from "@drakkarsoftware/octobot-protocol";
import type { Automation, AutomationContext } from "./automation.js";
import {
  newExecution,
  markRunning,
  markSuccess,
  markFailed,
  markCancelled,
} from "./execution.js";

export interface RunOptions {
  reason: string;
  state: unknown;
  signal?: AbortSignal;
}

export async function runAutomation<TState, TOutput>(
  automation: Automation<TState, TOutput>,
  opts: RunOptions,
): Promise<Execution> {
  const initial = newExecution({
    automationId: automation.id,
    reason: opts.reason,
    input: opts.state,
  });
  const signal = opts.signal ?? new AbortController().signal;

  if (signal.aborted) return markCancelled(initial);

  const ctx: AutomationContext = {
    executionId: initial.id,
    reason: opts.reason,
    signal,
    logger: getLogger(`Automation[${automation.id}]`),
  };
  const running = markRunning(initial);

  try {
    const result = await automation.run(ctx, opts.state as TState);
    if (signal.aborted) return markCancelled(running);
    return markSuccess(running, result);
  } catch (err) {
    if (signal.aborted) return markCancelled(running);
    return markFailed(running, err);
  }
}
