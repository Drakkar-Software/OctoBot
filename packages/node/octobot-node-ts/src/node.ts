// OctobotNode façade — registry + the single `run` entrypoint that turns an
// input AutomationsState into a nextState (with Execution rows appended).
// Pure: the lib never persists anything; the caller owns storage.

import type { AutomationsState, Execution } from "@drakkarsoftware/octobot-protocol";
import { Automation, AutomationRegistry, DefaultState } from "./automation.js";
import { runAutomation } from "./runner.js";
import {
  appendExecution,
  emptyState,
  latestForAutomation,
  latestOverall,
} from "./state.js";

export interface RunRequest<TState extends AutomationsState = AutomationsState> {
  state: TState;
  reason: string;
  /** When set, runs only this subset and bypasses each automation's `shouldRun`. */
  automationIds?: string[];
  /** Cooperative cancel for the whole tick. */
  signal?: AbortSignal;
}

export interface RunResult<TState extends AutomationsState = AutomationsState> {
  /** Records produced by automations that actually fired this tick. */
  executions: Execution[];
  /** Original state with the new executions folded in. */
  nextState: TState;
}

export class OctobotNode<TState extends AutomationsState = AutomationsState> {
  private readonly registry = new AutomationRegistry<TState>();

  registerAutomation<TOutput>(automation: Automation<TState, TOutput>): void {
    this.registry.register(automation);
  }

  unregisterAutomation(id: string): boolean {
    return this.registry.unregister(id);
  }

  hasAutomation(id: string): boolean {
    return this.registry.has(id);
  }

  listAutomations(): Automation<TState, unknown>[] {
    return this.registry.list();
  }

  /**
   * Trigger automations against `state`. Returns the executions produced and
   * the merged nextState. Automations run sequentially in registration order
   * so each can read the previous's effects via state helpers if needed.
   */
  async run(req: RunRequest<TState>): Promise<RunResult<TState>> {
    const explicit = req.automationIds !== undefined;
    const candidates = explicit
      ? req.automationIds!.map((id) => this.registry.get(id))
      : this.registry.list();

    const executions: Execution[] = [];
    let nextState = req.state;

    for (const automation of candidates) {
      if (req.signal?.aborted) break;

      if (!explicit && automation.shouldRun && !automation.shouldRun(nextState)) {
        continue;
      }

      const exec = await runAutomation(automation, {
        reason: req.reason,
        state: nextState,
        signal: req.signal,
      });
      executions.push(exec);
      nextState = appendExecution(nextState, exec) as TState;
    }

    return { executions, nextState };
  }

  // ---- pure state queries (forward to ./state helpers) ----

  latestForAutomation(state: TState, automationId: string): Execution | null {
    return latestForAutomation(state, automationId);
  }

  latestOverall(state: TState): Execution | null {
    return latestOverall(state);
  }
}

export function createOctobotNode<
  TState extends AutomationsState = DefaultState,
>(): OctobotNode<TState> {
  return new OctobotNode<TState>();
}

export { emptyState };
