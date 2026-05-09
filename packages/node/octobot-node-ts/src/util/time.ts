// Wraps Date.now so tests can stub it without monkey-patching the global.

let nowImpl: () => number = () => Date.now();

export function now(): number {
  return nowImpl();
}

export function setNowForTesting(impl: () => number): void {
  nowImpl = impl;
}

export function resetNow(): void {
  nowImpl = () => Date.now();
}
