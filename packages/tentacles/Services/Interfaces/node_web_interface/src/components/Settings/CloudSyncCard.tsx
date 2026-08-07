import { Link2, ShieldOff } from "lucide-react"
import { useEffect, useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import {
  DEFAULT_CLOUD_SYNC_COLLECTIONS,
  MIRROR_COLLECTIONS,
  nextCollectionsOnToggle,
} from "@/lib/cloud-sync-collections"
import { buildAuthHeader, fetchNodeConfig } from "@/lib/node-config"

type Status = "loading" | "ready" | "saving" | "error"

async function patchNodeConfig(body: Record<string, unknown>) {
  const res = await fetch("/api/v1/nodes/config", {
    method: "PATCH",
    headers: {
      Authorization: await buildAuthHeader(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

/** Compact inline section (no Card wrapper) — mounted under
 *  NodeConfigurationCard's "OctoBot interface" section rather than as its
 *  own dedicated card. */
export function CloudSyncSection() {
  const [status, setStatus] = useState<Status>("loading")
  const [error, setError] = useState("")
  const [enabled, setEnabled] = useState(false)
  const [collections, setCollections] = useState<string[]>([])
  const [configureOpen, setConfigureOpen] = useState(false)
  // Local draft edited inside the modal; only applied to `collections` (and
  // saved) on "Save" — closing without saving discards it.
  const [draft, setDraft] = useState<string[]>([])

  useEffect(() => {
    void (async () => {
      try {
        const data = await fetchNodeConfig()
        setEnabled(Boolean(data.cloud_sync_enabled))
        setCollections(
          Array.isArray(data.cloud_sync_collections)
            ? data.cloud_sync_collections
            : [],
        )
        setStatus("ready")
      } catch {
        setStatus("error")
        setError("Failed to load cloud sync configuration.")
      }
    })()
  }, [])

  const handleToggleEnabled = async (next: boolean) => {
    setStatus("saving")
    setError("")
    try {
      const data = await patchNodeConfig({ cloud_sync_enabled: next })
      setEnabled(Boolean(data.cloud_sync_enabled))
      setCollections(
        Array.isArray(data.cloud_sync_collections)
          ? data.cloud_sync_collections
          : [],
      )
      setStatus("ready")
    } catch (e) {
      setStatus("error")
      setError(e instanceof Error ? e.message : "Failed to update cloud sync")
    }
  }

  const openConfigure = () => {
    setDraft(collections)
    setConfigureOpen(true)
  }

  const handleSaveDraft = async () => {
    setStatus("saving")
    setError("")
    try {
      const data = await patchNodeConfig({ cloud_sync_collections: draft })
      setCollections(
        Array.isArray(data.cloud_sync_collections)
          ? data.cloud_sync_collections
          : [],
      )
      setStatus("ready")
      setConfigureOpen(false)
    } catch (e) {
      setStatus("error")
      setError(e instanceof Error ? e.message : "Failed to save collections")
    }
  }

  return (
    <>
      <div className="flex flex-col gap-3">
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          Cloud sync
        </span>
        <div className="flex items-center gap-3">
          <Checkbox
            id="cloud-sync-enabled"
            checked={enabled}
            disabled={status === "loading" || status === "saving"}
            onCheckedChange={(checked) =>
              void handleToggleEnabled(checked === true)
            }
          />
          <Label htmlFor="cloud-sync-enabled" className="text-sm font-medium">
            Enable cloud E2E-encrypted sync
          </Label>
        </div>
        <span className="text-xs text-muted-foreground">
          E2E-encrypted mirroring of this node&apos;s data to the shared cloud
          sync server. Required for website pairing to read anything.
        </span>
        {enabled && (
          <Button
            variant="outline"
            size="sm"
            onClick={openConfigure}
            className="self-start"
          >
            Configure
          </Button>
        )}
        {status === "error" && (
          <span className="text-xs text-destructive">{error}</span>
        )}
      </div>

      <Dialog open={configureOpen} onOpenChange={setConfigureOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Configure cloud sync</DialogTitle>
            <DialogDescription>
              Choose which collections are mirrored. Collections marked{" "}
              <Link2 className="inline size-3" /> can be shared with a paired
              third-party site; the rest sync only for your own devices.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-3">
            {MIRROR_COLLECTIONS.map((collection) => (
              <div key={collection.id} className="flex items-start gap-3">
                <Checkbox
                  id={`cloud-sync-collection-${collection.id}`}
                  checked={draft.includes(collection.id)}
                  onCheckedChange={(checked) =>
                    setDraft((prev) =>
                      nextCollectionsOnToggle(
                        prev,
                        collection.id,
                        checked === true,
                      ),
                    )
                  }
                  className="mt-0.5"
                />
                <div className="flex flex-col gap-0.5">
                  <Label
                    htmlFor={`cloud-sync-collection-${collection.id}`}
                    className="flex items-center gap-1.5 text-sm font-medium"
                  >
                    {collection.label}
                    {collection.thirdPartyEligible && (
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Badge variant="frost" className="px-1.5 py-0">
                            <Link2 />
                          </Badge>
                        </TooltipTrigger>
                        <TooltipContent side="top">
                          Can be shared with a paired third-party site
                        </TooltipContent>
                      </Tooltip>
                    )}
                  </Label>
                  <span className="text-xs text-muted-foreground">
                    {collection.description}
                  </span>
                </div>
              </div>
            ))}
            <div className="flex items-start gap-3 opacity-60">
              <Checkbox
                id="cloud-sync-collection-accounts-auth"
                checked={false}
                disabled
              />
              <div className="flex flex-col gap-0.5">
                <Label
                  htmlFor="cloud-sync-collection-accounts-auth"
                  className="flex items-center gap-1.5 text-sm font-medium"
                >
                  Exchange credentials
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Badge variant="secondary" className="px-1.5 py-0">
                        <ShieldOff />
                      </Badge>
                    </TooltipTrigger>
                    <TooltipContent side="top">
                      Never synced to the cloud, at any layer
                    </TooltipContent>
                  </Tooltip>
                </Label>
                <span className="text-xs text-muted-foreground">
                  Your exchange API keys stay on this node. This can never be
                  enabled.
                </span>
              </div>
            </div>
          </div>
          {status === "error" && (
            // The Card's own error span (above) renders behind this still-open
            // Dialog's overlay — a save failure was previously invisible until
            // the user closed the dialog and saw the underlying card. Mirrored
            // here so a failed "Save" is actually seen where it happens.
            <span className="text-xs text-destructive">{error}</span>
          )}
          <DialogFooter>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setDraft([...DEFAULT_CLOUD_SYNC_COLLECTIONS])}
            >
              Reset to defaults
            </Button>
            <DialogClose asChild>
              <Button variant="outline" type="button">
                Cancel
              </Button>
            </DialogClose>
            <Button
              onClick={() => void handleSaveDraft()}
              disabled={status === "saving"}
            >
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
