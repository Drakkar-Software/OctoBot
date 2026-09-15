import { useState } from "react"

import { MagicDnsRemoteUrlField } from "@/components/Common/MagicDnsRemoteUrlField"
import { SelectableTextBlock } from "@/components/Common/SelectableTextBlock"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { OCTOBOT_TAILSCALE_CONNECT_GUIDE_URL } from "@/lib/external-links"
import { buildTailscaleServeCommand } from "@/lib/secure-context"
import {
  TAILSCALE_ADMIN_CONSOLE_MACHINES_URL,
  TAILSCALE_FULL_DOMAIN_EXAMPLE,
  TAILSCALE_MAGICDNS_REACHABILITY_LEAD,
  TAILSCALE_REMOTE_ACCESS_DIALOG_TITLE,
  TAILSCALE_SERVE_NOT_ENABLED_ON_TAILNET_MESSAGE,
  TAILSCALE_SERVE_STARTED_RUNNING_MESSAGE,
} from "@/lib/ui-recovery-constants"

const TAILSCALE_UP_COMMAND = "tailscale up"
const TAILSCALE_COMMAND_ARIA_LABEL = "Tailscale command"

type TailscaleRemoteAccessDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function TailscaleRemoteAccessDialog({
  open,
  onOpenChange,
}: TailscaleRemoteAccessDialogProps) {
  const [magicDnsInput, setMagicDnsInput] = useState("")
  const pageHref =
    typeof window !== "undefined" ? window.location.href : "http://127.0.0.1:8000/app"
  const serveCommand = buildTailscaleServeCommand(pageHref)

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{TAILSCALE_REMOTE_ACCESS_DIALOG_TITLE}</DialogTitle>
          <DialogDescription asChild>
            <div className="flex flex-col gap-3 pt-1 text-sm text-muted-foreground">
              <ol className="list-decimal space-y-4 pl-5">
                <li className="space-y-2">
                  <p>
                    Install{" "}
                    <a
                      href="https://tailscale.com/download"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="underline underline-offset-2 text-foreground"
                    >
                      Tailscale
                    </a>{" "}
                    and sign in on the <strong>computer that runs the node</strong> and on{" "}
                    <strong>this computer</strong> (where you are viewing this page). On each
                    machine, <strong>start Tailscale</strong> or{" "}
                    <strong>run the command below</strong> until both show{" "}
                    <strong>Connected</strong> in Tailscale.
                  </p>
                  <SelectableTextBlock
                    value={TAILSCALE_UP_COMMAND}
                    ariaLabel={TAILSCALE_COMMAND_ARIA_LABEL}
                  />
                </li>
                <li className="space-y-2">
                  <p>
                    On the node computer, expose the node UI with{" "}
                    <code className="text-foreground">tailscale serve</code>:
                  </p>
                  <SelectableTextBlock
                    value={serveCommand}
                    ariaLabel={TAILSCALE_COMMAND_ARIA_LABEL}
                  />
                  <p>
                    If you see{" "}
                    <code className="text-foreground">
                      {TAILSCALE_SERVE_NOT_ENABLED_ON_TAILNET_MESSAGE}
                    </code>
                    , click the printed Tailscale link to enable Tailscale Serve. You should
                    then see{" "}
                    <code className="text-foreground">
                      {TAILSCALE_SERVE_STARTED_RUNNING_MESSAGE}
                    </code>{" "}
                    being printed in your terminal.
                  </p>
                </li>
                <li className="space-y-2">
                  <p>
                    On this computer, open the{" "}
                    <a
                      href={TAILSCALE_ADMIN_CONSOLE_MACHINES_URL}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="underline underline-offset-2 text-foreground"
                    >
                      Tailscale admin console Machines page
                    </a>
                    , select this node&apos;s computer, and copy the{" "}
                    <strong>Full domain</strong> field (for example{" "}
                    <code className="text-foreground">{TAILSCALE_FULL_DOMAIN_EXAMPLE}</code>
                    ).
                  </p>
                </li>
                <li>{TAILSCALE_MAGICDNS_REACHABILITY_LEAD}</li>
              </ol>
            </div>
          </DialogDescription>
        </DialogHeader>

        <MagicDnsRemoteUrlField
          pageHref={pageHref}
          value={magicDnsInput}
          onValueChange={setMagicDnsInput}
        />

        <DialogFooter className="flex-row flex-wrap justify-end gap-2">
          <Button type="button" variant="outline" asChild>
            <a
              href={OCTOBOT_TAILSCALE_CONNECT_GUIDE_URL}
              target="_blank"
              rel="noopener noreferrer"
            >
              Read the full Tailscale guide
            </a>
          </Button>
          <DialogClose asChild>
            <Button type="button" variant="secondary">
              Close
            </Button>
          </DialogClose>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
