import type { AutomationsState, Execution } from "@drakkarsoftware/octobot-protocol";
import type { Automation } from "./runner.js";
import { AutomationNotFoundError } from "./errors.js";
import { runAutomation } from "./runner.js";
import {
  appendExecution,
  emptyState,
  latestForAutomation,
  latestOverall,
} from "./state.js";

export interface RunRequest<TState extends AutomationsState = AutomationsState> {
  automations: Automation<TState, unknown>[];
  state: TState;
  reason: string;
  /** When set, runs only this subset and bypasses each automation's `shouldRun`. */
  automationIds?: string[];
  signal?: AbortSignal;
}

export interface RunResult<TState extends AutomationsState = AutomationsState> {
  executions: Execution[];
  nextState: TState;
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
      nextState = appendExecution(nextState, exec, () => ({
        id: automation.id,
        status: exec.status,
        metadata: automation.metadata,
      })) as TState;
    }

    return { executions, nextState };
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
