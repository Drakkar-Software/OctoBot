import type { Account, AccountsState, Action, AutomationState, AutomationsState, Execution } from "@drakkarsoftware/octobot-protocol";
import { getLogger } from "@drakkarsoftware/octobot-commons";
import type { ActionHandler } from "./actions.js";
import { actionToAutomation, applyExecutionToAction, assertHandlerExists } from "./actions.js";
import { emptyAccountsState, removeAccount, replaceAccount } from "./accounts.js";
import { ActionHandlerNotFoundError } from "./errors.js";
import { AutomationWorkflowActionType } from "./enums.js";
import type { AutomationWorkflowActionUpdate } from "./envelope.js";
import type { Automation } from "./runner.js";
import { runAutomation } from "./runner.js";
import { appendExecution, removeAutomationRow, replaceAutomationRow } from "./state.js";

export interface AutomationWorkflowInput<TState extends AutomationsState = AutomationsState> {
  automation: Automation<TState>;
  state: TState;
  accountsState?: AccountsState;
  reason: string;
  envelopes?: AutomationWorkflowActionUpdate[];
  actionHandlers?: Record<string, ActionHandler>;
  signal?: AbortSignal;
}

export interface AutomationWorkflowOutput<TState extends AutomationsState = AutomationsState> {
  state: TState;
  accountsState: AccountsState;
  execution: Execution;
  actionExecutions: Execution[];
  resolvedActions: Action[];
  accountMutations: { removed: string[] };
  automationMutations: { replaced: AutomationState[]; removed: string[] };
}

interface ParsedEnvelopes {
  priorityUserActions: Action[];
  tradingSignals: unknown[];
  forced: boolean;
}

function parseEnvelopes(
  envelopes: AutomationWorkflowActionUpdate[],
  automationId: string,
): ParsedEnvelopes {
  const result: ParsedEnvelopes = { priorityUserActions: [], tradingSignals: [], forced: false };
  for (const env of envelopes) {
    if (env.automationId !== automationId) continue;
    if (env.actionsType === AutomationWorkflowActionType.UserActions) {
      result.priorityUserActions.push(...env.userActions);
    } else if (env.actionsType === AutomationWorkflowActionType.TradingSignal) {
      result.tradingSignals.push(...env.tradingSignals);
    } else if (env.actionsType === AutomationWorkflowActionType.ForcedTrigger) {
      result.forced = true;
    }
  }
  return result;
}

export class AutomationWorkflow<TState extends AutomationsState = AutomationsState> {
  async executeAutomation(
    input: AutomationWorkflowInput<TState>,
  ): Promise<AutomationWorkflowOutput<TState>> {
    const { automation, reason, envelopes = [], actionHandlers, signal } = input;
    const log = getLogger(`AutomationWorkflow[${automation.id}]`);

    const { priorityUserActions, tradingSignals, forced } = parseEnvelopes(
      envelopes,
      automation.id,
    );

    // Fail-fast: validate all action handlers exist before running anything.
    for (const action of priorityUserActions) {
      assertHandlerExists(action.actionType, actionHandlers);
    }

    let nextState = input.state;
    let nextAccountsState: AccountsState = input.accountsState ?? emptyAccountsState();
    const actionExecutions: Execution[] = [];
    const resolvedActions: Action[] = [];
    const allAccountRemovals: string[] = [];
    const allAutomationReplacements: AutomationState[] = [];
    const allAutomationRemovals: string[] = [];

    // Priority user-actions pass.
    for (const action of priorityUserActions) {
      if (signal?.aborted) break;

      const stagedReplacements: Account[] = [];
      const stagedAccountRemovals: string[] = [];
      const stagedAutomationReplacements: AutomationState[] = [];
      const stagedAutomationRemovals: string[] = [];
      const handler = actionHandlers![action.actionType];
      const adapter = actionToAutomation(action, handler);

      const exec = await runAutomation(adapter, {
        reason,
        state: nextState,
        signal,
        accounts: nextAccountsState,
        replaceAccount: (a: Account) => stagedReplacements.push(a),
        removeAccount: (id: string) => stagedAccountRemovals.push(id),
        replaceAutomation: (row: AutomationState) => stagedAutomationReplacements.push(row),
        removeAutomation: (id: string) => stagedAutomationRemovals.push(id),
      });

      for (const account of stagedReplacements) {
        nextAccountsState = replaceAccount(nextAccountsState, account);
      }
      for (const id of stagedAccountRemovals) {
        nextAccountsState = removeAccount(nextAccountsState, id);
        allAccountRemovals.push(id);
      }
      for (const row of stagedAutomationReplacements) {
        nextState = replaceAutomationRow(nextState, row) as TState;
        allAutomationReplacements.push(row);
      }
      for (const id of stagedAutomationRemovals) {
        nextState = removeAutomationRow(nextState, id) as TState;
        allAutomationRemovals.push(id);
      }

      actionExecutions.push(exec);
      resolvedActions.push(applyExecutionToAction(action, exec));
      nextState = appendExecution(nextState, exec, () => ({
        id: adapter.id,
        status: exec.status,
        metadata: adapter.metadata,
      })) as TState;

      log.debug(`Action ${action.actionType} [${action.id}] → ${exec.status}`);
    }

    // Main automation pass.
    const mainExec = await runAutomation(automation, {
      reason,
      state: nextState,
      signal,
      accounts: nextAccountsState,
      tradingSignals,
      forced,
    });

    nextState = appendExecution(nextState, mainExec, () => ({
      id: automation.id,
      status: mainExec.status,
      metadata: automation.metadata,
    })) as TState;

    log.debug(`Automation [${automation.id}] → ${mainExec.status}`);

    return {
      state: nextState,
      accountsState: nextAccountsState,
      execution: mainExec,
      actionExecutions,
      resolvedActions,
      accountMutations: { removed: allAccountRemovals },
      automationMutations: { replaced: allAutomationReplacements, removed: allAutomationRemovals },
    };
  }
}
