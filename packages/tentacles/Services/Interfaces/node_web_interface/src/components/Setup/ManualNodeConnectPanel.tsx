import { NodeConnectAddressTabs } from "@/components/Setup/NodeConnectAddressTabs"
import { Button } from "@/components/ui/button"

type ManualNodeConnectPanelProps = {
  onSwitchToWeb: () => void
}

export function ManualNodeConnectPanel({ onSwitchToWeb }: ManualNodeConnectPanelProps) {
  return (
    <div className="flex flex-col gap-3">
      <NodeConnectAddressTabs audience="mobile" />

      <div className="flex flex-col items-center gap-3 pt-2 text-center text-sm text-muted-foreground">
        <p>
          Having troubles connecting to your node from the app? Start with the web
          version
        </p>
        <Button type="button" variant="outline" onClick={onSwitchToWeb}>
          Switch to web
        </Button>
      </div>
    </div>
  )
}
