import type { ReactNode } from "react"
import { Copy } from "lucide-react"

import { Button } from "@/components/ui/button"
import { copyTextToClipboard } from "@/lib/clipboard"

type CopyableNodeFieldProps = {
  label: string
  value: string
  loading?: boolean
}

function CopyableNodeField({ label, value, loading = false }: CopyableNodeFieldProps) {
  const displayValue = loading ? "Detecting…" : value

  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-sm font-medium">{label}</span>
      <div className="flex items-center justify-between gap-2 rounded-md border bg-muted px-3 py-2">
        <code className="text-sm break-all">{displayValue}</code>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="shrink-0"
          disabled={loading || !value}
          onClick={() => copyTextToClipboard(value, value)}
        >
          <Copy className="size-4" />
          Copy
        </Button>
      </div>
    </div>
  )
}

type SetupNodeAddressPanelProps = {
  hostname: string
  hostnameLabel?: string
  hostnameHelperText?: ReactNode
  showHostname?: boolean
  hostnameLoading?: boolean
}

export function SetupNodeAddressPanel({
  hostname,
  hostnameLabel = "Hostname or IP",
  hostnameHelperText,
  showHostname = true,
  hostnameLoading = false,
}: SetupNodeAddressPanelProps) {
  const nodePort = window.location.port || "8000"

  return (
    <div className="flex flex-col gap-3">
      {showHostname && (
        <>
          <CopyableNodeField
            label={hostnameLabel}
            value={hostname}
            loading={hostnameLoading}
          />
          {hostnameHelperText && (
            <p className="text-sm text-muted-foreground">{hostnameHelperText}</p>
          )}
        </>
      )}
      <CopyableNodeField label="Port" value={nodePort} />
    </div>
  )
}
