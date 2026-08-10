/**
 * Amber has exactly one job on this page: mark a panel that needs a
 * reachable OctoBot node. Never used decoratively elsewhere.
 */
export function NodeBadge({ reachable }: { reachable?: boolean }) {
  if (reachable === true) {
    return (
      <span className="inline-flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-wider text-live">
        <span className="h-1.5 w-1.5 rounded-full bg-live" />
        node reachable
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1.5 font-mono text-[11px] uppercase tracking-wider text-node-required">
      <span className="h-1.5 w-1.5 rounded-full bg-node-required" />
      needs a running node
    </span>
  )
}
