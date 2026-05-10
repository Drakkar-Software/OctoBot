import { getLogger } from "@drakkarsoftware/octobot-commons";
import type { AutomationMetadata, AutomationsState } from "@drakkarsoftware/octobot-protocol";
import type { Execution } from "@drakkarsoftware/octobot-protocol";
import type { Logger } from "@drakkarsoftware/octobot-commons";
import {
  newExecution,
  markRunning,
  markSuccess,
  markFailed,
  markCancelled,
} from "./execution.js";

export interface AutomationContext {
  executionId: string;
  reason: string;
  signal: AbortSignal;
  logger: Logger;
}

export interface Automation<TState = AutomationsState, TOutput = unknown> {
  id: string;
  metadata: AutomationMetadata;
  /** Optional gate — skipped when `automationIds` is explicit. */
  shouldRun?: (state: TState) => boolean;
  run: (ctx: AutomationContext, state: TState) => Promise<TOutput>;
}

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
