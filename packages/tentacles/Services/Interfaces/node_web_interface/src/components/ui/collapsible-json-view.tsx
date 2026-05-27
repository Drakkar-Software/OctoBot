import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { ChevronRight, Copy } from "lucide-react"
import { useState, type MouseEvent } from "react"
import { toast } from "sonner"

export const HIDDEN_JSON_FIELD = "_updated_fields"

export function formatJsonPrimitive(value: unknown): string {
  if (value === null) return "null"
  if (typeof value === "string") return JSON.stringify(value)
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value)
  }
  return JSON.stringify(value)
}

export function isJsonCollection(
  value: unknown,
): value is Record<string, unknown> | unknown[] {
  return typeof value === "object" && value !== null
}

export function getVisibleJsonObjectEntries(
  value: Record<string, unknown>,
): [string, unknown][] {
  return Object.entries(value).filter(([key]) => key !== HIDDEN_JSON_FIELD)
}

export function getJsonCollectionEntries(
  value: Record<string, unknown> | unknown[],
): [string, unknown][] {
  if (Array.isArray(value)) {
    return value.map((entry, index) => [String(index), entry])
  }
  return getVisibleJsonObjectEntries(value)
}

export function childNodesAreCollapsible(
  parentValue: Record<string, unknown> | unknown[],
): boolean {
  return !Array.isArray(parentValue)
}

export function formatJsonCollectionSummary(
  value: Record<string, unknown> | unknown[],
): string {
  if (Array.isArray(value)) {
    return `[${value.length}]`
  }
  return `{${getVisibleJsonObjectEntries(value).length}}`
}

export function formatJsonForClipboard(value: unknown): string {
  return JSON.stringify(value, null, 2)
}

function copyJsonToClipboard(value: unknown, description: string): void {
  void navigator.clipboard.writeText(formatJsonForClipboard(value)).then(() => {
    toast.success("Copied to clipboard", { description })
  })
}

function JsonCopyButton({
  value,
  label,
}: {
  value: unknown
  label: string | null
}) {
  const copyLabel = label ?? "JSON"
  const handleCopy = (event: MouseEvent<HTMLButtonElement>) => {
    event.preventDefault()
    event.stopPropagation()
    copyJsonToClipboard(value, copyLabel)
  }

  return (
    <Button
      type="button"
      variant="ghost"
      size="icon-sm"
      className="size-6 shrink-0 text-muted-foreground"
      aria-label={`Copy JSON for ${copyLabel}`}
      onClick={handleCopy}
      onPointerDown={(event) => event.stopPropagation()}
    >
      <Copy className="size-3" />
    </Button>
  )
}

function JsonCollectionLabel({
  label,
  collectionSummary,
}: {
  label: string | null
  collectionSummary: string
}) {
  return (
    <>
      {label !== null ? (
        <>
          <span className="text-muted-foreground">{label}:</span>{" "}
        </>
      ) : null}
      <span>{collectionSummary}</span>
    </>
  )
}

const JSON_TREE_CHILDREN_CLASS = "border-l border-border/50 pl-3"

function JsonCollectionChildren({
  entries,
  childCollapsible,
}: {
  entries: [string, unknown][]
  childCollapsible: boolean
}) {
  return (
    <div className={JSON_TREE_CHILDREN_CLASS}>
      {entries.map(([entryLabel, entryValue]) => (
        <JsonTreeNode
          key={entryLabel}
          label={entryLabel}
          value={entryValue}
          collapsible={childCollapsible}
        />
      ))}
    </div>
  )
}

function JsonTreeNode({
  label,
  value,
  collapsible = true,
}: {
  label: string | null
  value: unknown
  collapsible?: boolean
}) {
  const [isOpen, setIsOpen] = useState(true)

  if (!isJsonCollection(value)) {
    if (label !== null) {
      return (
        <div className="flex gap-1 break-all">
          <span className="shrink-0 text-muted-foreground">{label}:</span>
          <span>{formatJsonPrimitive(value)}</span>
        </div>
      )
    }
    return <div className="break-all">{formatJsonPrimitive(value)}</div>
  }

  const entries = getJsonCollectionEntries(value)
  const collectionSummary = formatJsonCollectionSummary(value)
  const childCollapsible = childNodesAreCollapsible(value)

  if (entries.length === 0) {
    return (
      <div className="flex items-start gap-1">
        <span className="min-w-0 flex-1 break-all">
          <JsonCollectionLabel
            label={label}
            collectionSummary={collectionSummary}
          />
        </span>
        <JsonCopyButton value={value} label={label} />
      </div>
    )
  }

  if (!collapsible) {
    return (
      <div>
        <div className="flex items-start gap-1">
          <span className="min-w-0 flex-1 break-all">
            <JsonCollectionLabel
              label={label}
              collectionSummary={collectionSummary}
            />
          </span>
          <JsonCopyButton value={value} label={label} />
        </div>
        <JsonCollectionChildren
          entries={entries}
          childCollapsible={childCollapsible}
        />
      </div>
    )
  }

  return (
    <details
      open={isOpen}
      onToggle={(event) => setIsOpen(event.currentTarget.open)}
      className="group/json [&_summary::-webkit-details-marker]:hidden"
    >
      <summary
        className={cn(
          "flex cursor-pointer list-none items-start gap-1",
          "rounded-sm hover:bg-background/60",
        )}
      >
        <ChevronRight
          className={cn(
            "mt-0.5 size-3.5 shrink-0 text-muted-foreground transition-transform",
            "group-open/json:rotate-90",
          )}
        />
        <span className="min-w-0 flex-1 break-all">
          <JsonCollectionLabel
            label={label}
            collectionSummary={collectionSummary}
          />
        </span>
        <JsonCopyButton value={value} label={label} />
      </summary>
      <JsonCollectionChildren
        entries={entries}
        childCollapsible={childCollapsible}
      />
    </details>
  )
}

export function CollapsibleJsonView({
  value,
  className,
}: {
  value: unknown
  className?: string
}) {
  return (
    <div
      className={cn(
        "min-h-0 flex-1 overflow-auto rounded-md border bg-muted p-3 font-mono text-xs leading-tight",
        className,
      )}
    >
      <JsonTreeNode label={null} value={value} />
    </div>
  )
}
