// The single source of truth for `StrategyKind`. Previously declared THREE
// times independently across @drakkar.software/octobot-sdk (types.ts,
// protocol/strategyPatch.ts, and re-derived in protocol/nodeState.ts usage) —
// consolidated here during the extraction. Every other file, in this package
// or in a consumer, imports this instead of redeclaring it.
export type StrategyKind = 'dca' | 'basket' | 'grid' | 'mm' | 'copy' | 'signal' | 'custom' | 'ai-agents'
