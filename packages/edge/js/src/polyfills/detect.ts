export type Runtime = "node" | "bun" | "deno" | "browser" | "react-native"

export function detectRuntime(): Runtime {
  const g = globalThis as any
  if (typeof g.Deno !== "undefined") return "deno"
  if (typeof g.Bun !== "undefined") return "bun"
  if (typeof navigator !== "undefined" && (navigator as any).product === "ReactNative") return "react-native"
  // Check for browser window or Web Worker / Service Worker environment
  if (typeof window !== "undefined") return "browser"
  if (typeof g.self === "object" && typeof g.WorkerGlobalScope !== "undefined") return "browser"
  return "node"
}
