/** Shared polling primitives for sequenced node orchestrators. */
export const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms))
export const pollDelay = (n: number) => Math.min(2000 + n * 1500, 8000)
