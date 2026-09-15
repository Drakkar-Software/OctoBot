import { buildSameComputerLoopbackUrl } from "@/lib/secure-context"
import {
  INSECURE_CONTEXT_OPTION_LOCAL_SUBLABEL,
  INSECURE_CONTEXT_OPTION_LOCAL_TITLE,
  INSECURE_CONTEXT_OPTION_REMOTE_TITLE,
  INSECURE_CONTEXT_REMOTE_LEAD,
  INSECURE_CONTEXT_SAME_COMPUTER_LEAD,
  INSECURE_CONTEXT_WHY_ADDRESS_AFTER,
  INSECURE_CONTEXT_WHY_ADDRESS_BEFORE,
  INSECURE_CONTEXT_WHY_LEAD,
  TAILSCALE_REMOTE_ACCESS_BUTTON_LABEL,
} from "@/lib/ui-recovery-constants"
import { Button } from "@/components/ui/button"

type InsecureContextGuidanceProps = {
  onSetUpRemoteAccessClick: () => void
}

export function InsecureContextGuidance({
  onSetUpRemoteAccessClick,
}: InsecureContextGuidanceProps) {
  const pageHref =
    typeof window !== "undefined" ? window.location.href : ""
  const loopbackUrl =
    typeof window !== "undefined"
      ? buildSameComputerLoopbackUrl(window.location.href)
      : "http://127.0.0.1:8000/app"

  return (
    <div className="space-y-4 text-sm text-muted-foreground">
      <div className="space-y-2">
        <p>{INSECURE_CONTEXT_WHY_LEAD}</p>
        {pageHref !== "" ? (
          <p>
            {INSECURE_CONTEXT_WHY_ADDRESS_BEFORE}
            <span className="break-all font-mono text-foreground">{pageHref}</span>
            {INSECURE_CONTEXT_WHY_ADDRESS_AFTER}
          </p>
        ) : null}
      </div>
      <div className="space-y-3 rounded-md border border-border bg-muted/20 p-4">
        <p className="font-medium text-foreground">{INSECURE_CONTEXT_OPTION_LOCAL_TITLE}</p>
        <p className="text-xs">{INSECURE_CONTEXT_OPTION_LOCAL_SUBLABEL}</p>
        <p>{INSECURE_CONTEXT_SAME_COMPUTER_LEAD}</p>
        <p>
          <a
            href={loopbackUrl}
            className="break-all underline underline-offset-2 text-foreground"
          >
            {loopbackUrl}
          </a>
        </p>
      </div>
      <div
        className="space-y-3 rounded-md border border-border bg-muted/20 p-4"
        data-testid="insecure-context-option-remote"
      >
        <p className="font-medium text-foreground">{INSECURE_CONTEXT_OPTION_REMOTE_TITLE}</p>
        <p>{INSECURE_CONTEXT_REMOTE_LEAD}</p>
        <Button type="button" variant="outline" onClick={onSetUpRemoteAccessClick}>
          {TAILSCALE_REMOTE_ACCESS_BUTTON_LABEL}
        </Button>
      </div>
    </div>
  )
}
