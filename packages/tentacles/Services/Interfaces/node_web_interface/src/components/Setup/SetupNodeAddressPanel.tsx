import type { ReactNode } from "react"
import { Copy, RefreshCw } from "lucide-react"

import { Button } from "@/components/ui/button"
import { copyTextToClipboard } from "@/lib/clipboard"
import { cn } from "@/lib/utils"

type CopyableNodeFieldProps = {
  label: string
  value: string
  loading?: boolean
  onRefresh?: () => void
  refreshPending?: boolean
  refreshAriaLabel?: string
}

function CopyableNodeField({
  label,
  value,
  loading = false,
  onRefresh,
  refreshPending = false,
  refreshAriaLabel = "Refresh",
}: CopyableNodeFieldProps) {
  const displayValue = loading ? "Detecting…" : value

  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-sm font-medium">{label}</span>
      <div className="flex items-center justify-between gap-2 rounded-md border bg-muted px-3 py-2">
        <code className="text-sm break-all">{displayValue}</code>
        <div className="flex shrink-0 items-center gap-2">
          {onRefresh && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              disabled={loading || refreshPending}
              aria-label={refreshAriaLabel}
              onClick={onRefresh}
            >
              <RefreshCw
                className={cn("size-4", refreshPending && "animate-spin")}
              />
              Refresh
            </Button>
          )}
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={loading || !value}
            onClick={() => copyTextToClipboard(value, value)}
          >
            <Copy className="size-4" />
            Copy
          </Button>
        </div>
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
  onHostnameRefresh?: () => void
  hostnameRefreshPending?: boolean
  hostnameRefreshAriaLabel?: string
}

export function SetupNodeAddressPanel({
  hostname,
  hostnameLabel = "Hostname or IP",
  hostnameHelperText,
  showHostname = true,
  hostnameLoading = false,
  onHostnameRefresh,
  hostnameRefreshPending = false,
  hostnameRefreshAriaLabel,
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
            onRefresh={onHostnameRefresh}
            refreshPending={hostnameRefreshPending}
            refreshAriaLabel={hostnameRefreshAriaLabel}
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
