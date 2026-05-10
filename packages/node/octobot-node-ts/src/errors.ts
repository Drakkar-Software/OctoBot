export class NodeError extends Error {
  constructor(message?: string) {
    super(message);
    this.name = new.target.name;
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

export class AutomationNotFoundError extends NodeError {
  constructor(public readonly automationId: string) {
    super(`Automation not found: ${automationId}`);
  }
}

export class ExecutionFailedError extends NodeError {
  constructor(
    public readonly automationId: string,
    public readonly cause: unknown,
  ) {
    super(`Automation ${automationId} failed: ${(cause as Error)?.message ?? String(cause)}`);
  }
}

export class ExecutionCancelledError extends NodeError {
  constructor(public readonly automationId: string) {
    super(`Automation ${automationId} was cancelled before completion`);
  }
}
