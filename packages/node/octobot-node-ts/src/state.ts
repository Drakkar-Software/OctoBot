// Pure helpers over the protocol-typed state. The lib never mutates the input
// state — every helper returns a new object with the relevant fields replaced.

import type {
  AutomationsState,
  AutomationState,
  Execution,
} from "@drakkarsoftware/octobot-protocol";

const PROTOCOL_VERSION = "1.0.0";

export function emptyState(): AutomationsState {
  return { version: PROTOCOL_VERSION, automations: [] };
}

export function findAutomationState(
  state: AutomationsState,
  automationId: string,
): AutomationState | null {
  return state.automations?.find((a) => a.id === automationId) ?? null;
}

/**
 * Append an Execution to the automation's history (creating an AutomationState
 * row if the automation isn't represented yet) and bump `last_execution`.
 */
export function appendExecution(
  state: AutomationsState,
  execution: Execution,
  ifMissing?: () => AutomationState,
): AutomationsState {
  const automations = state.automations ?? [];
  const idx = automations.findIndex((a) => a.id === execution.automationId);

  let updatedRow: AutomationState;
  let nextAutomations: AutomationState[];
  if (idx >= 0) {
    const existing = automations[idx];
    updatedRow = {
      ...existing,
      executions: [...(existing.executions ?? []), execution],
      lastExecution: execution,
    };
    nextAutomations = automations.slice();
    nextAutomations[idx] = updatedRow;
  } else {
    const seed = ifMissing?.() ?? {
      id: execution.automationId,
      status: execution.status,
      metadata: { name: execution.automationId, description: "" },
    };
    updatedRow = {
      ...seed,
      executions: [...(seed.executions ?? []), execution],
      lastExecution: execution,
    };
    nextAutomations = [...automations, updatedRow];
  }

  return { ...state, automations: nextAutomations };
}

export function replaceExecution(
  state: AutomationsState,
  execution: Execution,
): AutomationsState {
  const automations = state.automations ?? [];
  const idx = automations.findIndex((a) => a.id === execution.automationId);
  if (idx < 0) return appendExecution(state, execution);

  const existing = automations[idx];
  const history = existing.executions ?? [];
  const execIdx = history.findIndex((e) => e.id === execution.id);
  const nextHistory = execIdx >= 0 ? history.slice() : [...history, execution];
  if (execIdx >= 0) nextHistory[execIdx] = execution;

  const lastIsThisExecution = existing.lastExecution?.id === execution.id;
  const updatedRow: AutomationState = {
    ...existing,
    executions: nextHistory,
    lastExecution: lastIsThisExecution ? execution : existing.lastExecution ?? execution,
  };
  const nextAutomations = automations.slice();
  nextAutomations[idx] = updatedRow;
  return { ...state, automations: nextAutomations };
}

export function latestForAutomation(
  state: AutomationsState,
  automationId: string,
): Execution | null {
  const row = findAutomationState(state, automationId);
  if (row?.lastExecution) return row.lastExecution;
  const history = row?.executions;
  return history && history.length > 0 ? history[history.length - 1] : null;
}

export function replaceAutomationRow(
  state: AutomationsState,
  row: AutomationState,
): AutomationsState {
  const automations = state.automations ?? [];
  const idx = automations.findIndex((a) => a.id === row.id);
  if (idx < 0) return { ...state, automations: [...automations, row] };
  const next = automations.slice();
  next[idx] = row;
  return { ...state, automations: next };
}

export function removeAutomationRow(
  state: AutomationsState,
  automationId: string,
): AutomationsState {
  const automations = state.automations ?? [];
  return { ...state, automations: automations.filter((a) => a.id !== automationId) };
}

export function latestOverall(state: AutomationsState): Execution | null {
  let best: Execution | null = null;
  for (const a of state.automations ?? []) {
    const candidate = a.lastExecution ?? a.executions?.[a.executions.length - 1] ?? null;
    if (candidate && (!best || candidate.startedAt > best.startedAt)) best = candidate;
  }
  return best;
}
