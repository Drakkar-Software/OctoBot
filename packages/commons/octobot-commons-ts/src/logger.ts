// Browser-safe logger replacement for octobot_commons.logging. Callers can swap
// in a custom backend (pino, loglevel, datadog, etc.) without touching downstream
// packages.

export interface LoggerBackend {
  debug(message: string, ...args: unknown[]): void;
  info(message: string, ...args: unknown[]): void;
  warning(message: string, ...args: unknown[]): void;
  error(message: string, ...args: unknown[]): void;
  exception(err: unknown, message?: string): void;
}

class ConsoleBackend implements LoggerBackend {
  debug(message: string, ...args: unknown[]): void {
    console.debug(message, ...args);
  }
  info(message: string, ...args: unknown[]): void {
    console.info(message, ...args);
  }
  warning(message: string, ...args: unknown[]): void {
    console.warn(message, ...args);
  }
  error(message: string, ...args: unknown[]): void {
    console.error(message, ...args);
  }
  exception(err: unknown, message?: string): void {
    if (message) console.error(message, err);
    else console.error(err);
  }
}

let backend: LoggerBackend = new ConsoleBackend();

export function setLoggerBackend(b: LoggerBackend): void {
  backend = b;
}

export class Logger {
  constructor(public readonly name: string) {}

  private prefix(): string {
    return `[${this.name}]`;
  }

  debug(message: string, ...args: unknown[]): void {
    backend.debug(`${this.prefix()} ${message}`, ...args);
  }

  info(message: string, ...args: unknown[]): void {
    backend.info(`${this.prefix()} ${message}`, ...args);
  }

  warning(message: string, ...args: unknown[]): void {
    backend.warning(`${this.prefix()} ${message}`, ...args);
  }

  error(message: string, ...args: unknown[]): void {
    backend.error(`${this.prefix()} ${message}`, ...args);
  }

  exception(err: unknown, message?: string): void {
    backend.exception(err, message ? `${this.prefix()} ${message}` : this.prefix());
  }
}

export function getLogger(name: string): Logger {
  return new Logger(name);
}
