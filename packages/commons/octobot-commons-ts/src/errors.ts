// Subset port of octobot_commons.errors. Only the error classes downstream
// packages may need to catch are reproduced; the rest stay in the Python source.

export class CommonsError extends Error {
  constructor(message?: string) {
    super(message);
    this.name = new.target.name;
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

export class ConfigError extends CommonsError {}
export class RemoteConfigError extends ConfigError {}

export class MissingDataError extends CommonsError {}
export class MissingExchangeDataError extends CommonsError {}
export class ExecutionAborted extends CommonsError {}
export class UnsupportedError extends CommonsError {}
export class InvalidUserInputError extends CommonsError {}
