import { getLogger } from "@drakkarsoftware/octobot-commons";
import type { Account, AccountsState, AutomationMetadata, AutomationsState, Execution } from "@drakkarsoftware/octobot-protocol";
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
  /** Snapshot of account state at the start of this automation's run. */
  accounts?: AccountsState;
  /** Stage an updated account — visible to subsequent actions/automations in the same workflow pass. */
  replaceAccount?: (account: Account) => void;
  /** Trading signals forwarded from a TRADING_SIGNAL envelope. */
  tradingSignals?: unknown[];
  /** True when this run was triggered by a FORCED_TRIGGER envelope, bypassing shouldRun. */
  forced?: boolean;
}

export interface Automation<TState = AutomationsState, TOutput = unknown> {
  id: string;
  metadata: AutomationMetadata;
  /** Optional gate — skipped when `automationIds` is explicit or `ctx.forced` is true. */
  shouldRun?: (state: TState) => boolean;
  run: (ctx: AutomationContext, state: TState) => Promise<TOutput>;
}

export interface RunOptions {
  reason: string;
  state: unknown;
  signal?: AbortSignal;
  accounts?: AccountsState;
  replaceAccount?: (account: Account) => void;
  tradingSignals?: unknown[];
  forced?: boolean;
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
    accounts: opts.accounts,
    replaceAccount: opts.replaceAccount,
    tradingSignals: opts.tradingSignals,
    forced: opts.forced,
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
