import { SelectableTextBlock } from "@/components/Common/SelectableTextBlock"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  buildHttpsNodeUrlFromHostname,
  parseMagicDnsHostnameInput,
} from "@/lib/secure-context"
import {
  MAGIC_DNS_INPUT_LABEL,
  MAGIC_DNS_INPUT_PLACEHOLDER,
  MAGIC_DNS_OPEN_IN_BROWSER_LABEL,
  MAGIC_DNS_REMOTE_URL_LABEL,
  TAILSCALE_AVOID_IP_HTTPS_WARNING,
} from "@/lib/ui-recovery-constants"

type MagicDnsRemoteUrlFieldProps = {
  pageHref: string
  value: string
  onValueChange: (value: string) => void
}

const REMOTE_URL_ARIA_LABEL = "Remote HTTPS URL"

export function MagicDnsRemoteUrlField({
  pageHref,
  value,
  onValueChange,
}: MagicDnsRemoteUrlFieldProps) {
  const trimmed = value.trim()
  const parsed =
    trimmed === "" ? null : parseMagicDnsHostnameInput(value)
  const remoteUrl =
    parsed?.ok === true
      ? buildHttpsNodeUrlFromHostname(parsed.hostname, pageHref)
      : null
  const errorMessage =
    trimmed !== "" && parsed?.ok === false ? parsed.message : null

  return (
    <div className="flex flex-col gap-3 border-t pt-4">
      <div className="flex flex-col gap-2">
        <Label htmlFor="magic-dns-hostname">{MAGIC_DNS_INPUT_LABEL}</Label>
        <Input
          id="magic-dns-hostname"
          type="text"
          placeholder={MAGIC_DNS_INPUT_PLACEHOLDER}
          value={value}
          onChange={(event) => onValueChange(event.target.value)}
          autoComplete="off"
        />
        {errorMessage ? (
          <p className="text-sm text-destructive">{errorMessage}</p>
        ) : null}
      </div>
      {remoteUrl ? (
        <div className="flex flex-col gap-2">
          <span className="text-sm font-medium">{MAGIC_DNS_REMOTE_URL_LABEL}</span>
          <SelectableTextBlock
            value={remoteUrl}
            ariaLabel={REMOTE_URL_ARIA_LABEL}
          />
          <a
            href={remoteUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm underline underline-offset-2 w-fit"
          >
            {MAGIC_DNS_OPEN_IN_BROWSER_LABEL}
          </a>
          <p className="rounded-md border border-border bg-muted/20 p-3 text-xs text-muted-foreground">
            {TAILSCALE_AVOID_IP_HTTPS_WARNING}
          </p>
        </div>
      ) : null}
    </div>
  )
}
