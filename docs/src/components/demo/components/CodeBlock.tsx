import { useState } from "react"

/**
 * The one code-block treatment used everywhere on the page, wire side and
 * paper side alike — a page whose entire value is code should never show
 * two visually distinct code surfaces (see CLAUDE.md, "one code treatment").
 *
 * Always copy-exact: `code` must be the real snippet that produced what is
 * on screen, never pseudocode. Set `recorded` when the panel above this
 * block ran against a fixture rather than a live call — it renders a
 * visible stamp rather than a quiet omission.
 */
export function CodeBlock({
  code,
  language = "ts",
  recorded,
}: {
  code: string
  language?: string
  recorded?: string
}) {
  const [copied, setCopied] = useState(false)

  const onCopy = () => {
    void navigator.clipboard.writeText(code).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    })
  }

  return (
    <div className="relative rounded-none border border-wire-rule bg-wire-surface">
      <div className="flex items-center justify-between border-b border-wire-rule px-3 py-1.5">
        <span className="font-mono text-[11px] uppercase tracking-wider text-wire-muted">
          {language}
        </span>
        <div className="flex items-center gap-2">
          {recorded ? (
            <span className="rounded-none border border-node-required/60 px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wider text-node-required">
              {recorded}
            </span>
          ) : null}
          <button
            type="button"
            onClick={onCopy}
            className="font-mono text-[11px] text-wire-muted transition-colors hover:text-live"
          >
            {copied ? "copied" : "copy"}
          </button>
        </div>
      </div>
      <pre className="overflow-x-auto px-4 py-3 font-mono text-[13px] leading-relaxed text-wire-ink">
        <code>{code}</code>
      </pre>
    </div>
  )
}
