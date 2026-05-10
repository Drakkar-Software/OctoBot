import type { Action, AccountsState, AutomationState, AutomationsState, Execution } from "@drakkarsoftware/octobot-protocol";
import type { ActionHandler } from "./actions.js";
import { emptyAccountsState, removeAccount, replaceAccount } from "./accounts.js";
import { AutomationNotFoundError } from "./errors.js";
import type { AutomationWorkflowActionUpdate } from "./envelope.js";
import type { Automation } from "./runner.js";
import { runAutomation } from "./runner.js";
import { AutomationWorkflow, type AutomationWorkflowOutput } from "./workflow.js";
import {
  appendExecution,
  emptyState,
  latestForAutomation,
  latestOverall,
  removeAutomationRow,
  replaceAutomationRow,
} from "./state.js";

export interface RunRequest<TState extends AutomationsState = AutomationsState> {
  automations: Automation<TState, unknown>[];
  state: TState;
  reason: string;
  /** When set, runs only this subset and bypasses each automation's `shouldRun`. */
  automationIds?: string[];
  /** Optional account state threaded into each automation's context. */
  accountsState?: AccountsState;
  /** Envelopes (user actions / trading signals / forced triggers) per automation. */
  envelopes?: AutomationWorkflowActionUpdate[];
  /** Action handlers keyed by `action.actionType`. Required when envelopes carry USER_ACTIONS. */
  actionHandlers?: Record<string, ActionHandler>;
  /**
   * When true, all automations run concurrently against the same input state via Promise.all.
   * Each automation is isolated — they cannot observe each other's mid-run executions.
   * When false (default), automations run sequentially; each sees the previous one's folded state.
   */
  parallel?: boolean;
  signal?: AbortSignal;
}

export interface RunResult<TState extends AutomationsState = AutomationsState> {
  executions: Execution[];
  nextState: TState;
  nextAccountsState: AccountsState;
  resolvedActions: Action[];
}

function mergeAccountsState(
  base: AccountsState,
  outputs: AutomationWorkflowOutput[],
): AccountsState {
  let merged = base;
  for (const out of outputs) {
    for (const account of out.accountsState.accounts ?? []) {
      merged = replaceAccount(merged, account);
    }
    for (const id of out.accountMutations.removed) {
      merged = removeAccount(merged, id);
    }
  }
  return merged;
}

function mergeAutomationsState<TState extends AutomationsState>(
  base: TState,
  outputs: AutomationWorkflowOutput[],
): TState {
  let merged = base;
  for (const out of outputs) {
    for (const row of out.automationMutations.replaced) {
      merged = replaceAutomationRow(merged, row) as TState;
    }
    for (const id of out.automationMutations.removed) {
      merged = removeAutomationRow(merged, id) as TState;
    }
  }
  return merged;
}

function foldExecutionsIntoState<TState extends AutomationsState>(
  state: TState,
  outputs: AutomationWorkflowOutput[],
): TState {
  let next = state;
  for (const out of outputs) {
    for (const exec of [...out.actionExecutions, out.execution]) {
      next = appendExecution(next, exec, () => ({
        id: exec.automationId,
        status: exec.status,
        metadata: { name: exec.automationId, description: "" },
      })) as TState;
    }
  }
  return next;
}

export class OctobotNode<TState extends AutomationsState = AutomationsState> {
  async run(req: RunRequest<TState>): Promise<RunResult<TState>> {
    const explicit = req.automationIds !== undefined;
    const candidates = explicit
      ? req.automationIds!.map((id) => {
          const a = req.automations.find((x) => x.id === id);
          if (!a) throw new AutomationNotFoundError(id);
          return a;
        })
      : req.automations;

    const hasEnvelopes = (req.envelopes?.length ?? 0) > 0;
    const inputAccountsState: AccountsState = req.accountsState ?? emptyAccountsState();

    if (req.parallel) {
      return this.runParallel(req, candidates, hasEnvelopes, inputAccountsState, explicit);
    }
    return this.runSequential(req, candidates, hasEnvelopes, inputAccountsState, explicit);
  }

  private async runSequential(
    req: RunRequest<TState>,
    candidates: Automation<TState, unknown>[],
    hasEnvelopes: boolean,
    inputAccountsState: AccountsState,
    explicit: boolean,
  ): Promise<RunResult<TState>> {
    const workflow = hasEnvelopes ? new AutomationWorkflow<TState>() : null;
    const executions: Execution[] = [];
    const resolvedActions: Action[] = [];
    let nextState = req.state;
    let nextAccountsState = inputAccountsState;

    for (const automation of candidates) {
      if (req.signal?.aborted) break;

      if (workflow) {
        const out = await workflow.executeAutomation({
          automation,
          state: nextState,
          accountsState: nextAccountsState,
          reason: req.reason,
          envelopes: req.envelopes,
          actionHandlers: req.actionHandlers,
          signal: req.signal,
        });
        executions.push(...out.actionExecutions, out.execution);
        resolvedActions.push(...out.resolvedActions);
        nextState = out.state;
        nextAccountsState = out.accountsState;
      } else {
        if (!explicit && automation.shouldRun && !automation.shouldRun(nextState)) continue;

        const exec = await runAutomation(automation, {
          reason: req.reason,
          state: nextState,
          signal: req.signal,
          accounts: nextAccountsState,
        });
        executions.push(exec);
        nextState = appendExecution(nextState, exec, () => ({
          id: automation.id,
          status: exec.status,
          metadata: automation.metadata,
        })) as TState;
      }
    }

    return { executions, nextState, nextAccountsState, resolvedActions };
  }

  private async runParallel(
    req: RunRequest<TState>,
    candidates: Automation<TState, unknown>[],
    hasEnvelopes: boolean,
    inputAccountsState: AccountsState,
    explicit: boolean,
  ): Promise<RunResult<TState>> {
    // All automations run against the same input state concurrently.
    if (hasEnvelopes) {
      const workflow = new AutomationWorkflow<TState>();
      const outputs = await Promise.all(
        candidates.map((automation) =>
          workflow.executeAutomation({
            automation,
            state: req.state,
            accountsState: inputAccountsState,
            reason: req.reason,
            envelopes: req.envelopes,
            actionHandlers: req.actionHandlers,
            signal: req.signal,
          }),
        ),
      );

      const executions = outputs.flatMap((o) => [...o.actionExecutions, o.execution]);
      const resolvedActions = outputs.flatMap((o) => o.resolvedActions);
      const withExecs = foldExecutionsIntoState(req.state, outputs);
      const nextState = mergeAutomationsState(withExecs, outputs);
      const nextAccountsState = mergeAccountsState(inputAccountsState, outputs);
      return { executions, nextState, nextAccountsState, resolvedActions };
    }

    const eligible = explicit
      ? candidates
      : candidates.filter((a) => !a.shouldRun || a.shouldRun(req.state));

    const execs = await Promise.all(
      eligible.map((automation) =>
        runAutomation(automation, {
          reason: req.reason,
          state: req.state,
          signal: req.signal,
          accounts: inputAccountsState,
        }),
      ),
    );

    let nextState = req.state;
    for (let i = 0; i < eligible.length; i++) {
      nextState = appendExecution(nextState, execs[i], () => ({
        id: eligible[i].id,
        status: execs[i].status,
        metadata: eligible[i].metadata,
      })) as TState;
    }

    return {
      executions: execs,
      nextState,
      nextAccountsState: inputAccountsState,
      resolvedActions: [],
    };
  }

  latestForAutomation(state: TState, automationId: string): Execution | null {
    return latestForAutomation(state, automationId);
  }

  latestOverall(state: TState): Execution | null {
    return latestOverall(state);
  }
}

export function createOctobotNode<
  TState extends AutomationsState = AutomationsState,
>(): OctobotNode<TState> {
  return new OctobotNode<TState>();
}

export { emptyState };
