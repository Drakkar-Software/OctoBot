import { NodeConnectAddressTabs } from "@/components/Setup/NodeConnectAddressTabs"
import { Button } from "@/components/ui/button"
import {
  OCTOBOT_CONNECT_GUIDE_COMMON_ISSUES_URL,
  OCTOBOT_CONNECT_GUIDE_URL,
} from "@/lib/external-links"

type ManualNodeConnectPanelProps = {
  onSwitchToWeb: () => void
}

export function ManualNodeConnectPanel({ onSwitchToWeb }: ManualNodeConnectPanelProps) {
  return (
    <div className="flex flex-col gap-3">
      <NodeConnectAddressTabs audience="mobile" />

      <div className="flex flex-col items-center gap-3 pt-2 text-center text-sm text-muted-foreground">
        <p>
          Having troubles connecting to your node from the app? See our{" "}
          <a
            href={OCTOBOT_CONNECT_GUIDE_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="underline underline-offset-4 hover:text-foreground"
          >
            full connect guide
          </a>{" "}
          or{" "}
          <a
            href={OCTOBOT_CONNECT_GUIDE_COMMON_ISSUES_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="underline underline-offset-4 hover:text-foreground"
          >
            common issues
          </a>
          .
        </p>
        <p>You can also start with the web version.</p>
        <Button type="button" variant="outline" onClick={onSwitchToWeb}>
          Switch to web
        </Button>
      </div>
    </div>
  )
}
