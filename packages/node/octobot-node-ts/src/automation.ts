import type { Logger } from "@drakkarsoftware/octobot-commons";
import type { AutomationsState } from "@drakkarsoftware/octobot-protocol";
import { DuplicateAutomationError, AutomationNotFoundError } from "./errors.js";

/**
 * The state passed to an automation is, by default, the protocol's full
 * AutomationsState bag. Hosts can extend it via the generic param if they
 * embed extra fields (current portfolio, prices, …).
 */
export type DefaultState = AutomationsState;

export interface AutomationContext {
  /** ID of the Execution record being filled in for this run. */
  executionId: string;
  /** Free-form why this run was triggered, copied onto the Execution. */
  reason: string;
  /**
   * Cooperative cancel — automations should poll this between expensive steps.
   * If aborted before the run reports a result, the runner records `cancelled`.
   */
  signal: AbortSignal;
  logger: Logger;
}

export interface Automation<TState = DefaultState, TOutput = unknown> {
  id: string;
  name: string;
  description?: string;
  /**
   * Optional gate. Returns true to fire when included in `node.run({ state })`
   * without an explicit `automationIds` list. Explicit subsets bypass this.
   */
  shouldRun?: (state: TState) => boolean;
  run: (ctx: AutomationContext, state: TState) => Promise<TOutput>;
}

export class AutomationRegistry<TState = DefaultState> {
  private readonly byId = new Map<string, Automation<TState, unknown>>();
  private readonly order: string[] = [];

  register<TOutput>(automation: Automation<TState, TOutput>): void {
    if (this.byId.has(automation.id)) {
      throw new DuplicateAutomationError(automation.id);
    }
    this.byId.set(automation.id, automation as Automation<TState, unknown>);
    this.order.push(automation.id);
  }

  unregister(id: string): boolean {
    if (!this.byId.delete(id)) return false;
    const idx = this.order.indexOf(id);
    if (idx >= 0) this.order.splice(idx, 1);
    return true;
  }

  get(id: string): Automation<TState, unknown> {
    const a = this.byId.get(id);
    if (!a) throw new AutomationNotFoundError(id);
    return a;
  }

  has(id: string): boolean {
    return this.byId.has(id);
  }

  list(): Automation<TState, unknown>[] {
    return this.order.map((id) => this.byId.get(id) as Automation<TState, unknown>);
  }

  size(): number {
    return this.byId.size;
  }
}
