// Direct replacements for the asyncio idioms used across octobot packages.

export class Deferred<T = void> {
  private _resolve!: (v: T | PromiseLike<T>) => void;
  private _reject!: (reason?: unknown) => void;
  readonly promise: Promise<T>;
  private _settled = false;

  constructor() {
    this.promise = new Promise<T>((resolve, reject) => {
      this._resolve = resolve;
      this._reject = reject;
    });
  }

  resolve(value: T): void {
    if (!this._settled) {
      this._settled = true;
      this._resolve(value);
    }
  }

  reject(reason?: unknown): void {
    if (!this._settled) {
      this._settled = true;
      this._reject(reason);
    }
  }

  get settled(): boolean {
    return this._settled;
  }
}

// asyncio.Event — set/clear/wait
export class AsyncEvent {
  private _deferred = new Deferred<void>();
  private _isSet = false;

  set(): void {
    if (!this._isSet) {
      this._isSet = true;
      this._deferred.resolve();
    }
  }

  clear(): void {
    if (this._isSet) {
      this._isSet = false;
      this._deferred = new Deferred<void>();
    }
  }

  isSet(): boolean {
    return this._isSet;
  }

  async wait(): Promise<void> {
    if (this._isSet) return;
    return this._deferred.promise;
  }
}

export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// "Best-effort" fire-and-forget. Reports rejections so we don't get unhandled
// promise warnings in browsers.
export function fireAndForget(
  task: () => Promise<unknown>,
  onError?: (err: unknown) => void,
): void {
  void task().catch((err) => {
    if (onError) onError(err);
    else console.error("[octobot-commons] background task failed:", err);
  });
}

// Yield to the event loop one tick — equivalent to asyncio.sleep(0).
export function nextTick(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 0));
}
