import type { ReactNode } from "react"

/**
 * The only section wrapper on the page. `weight` controls the visual
 * emphasis directly — stations are deliberately unequal (the derivation
 * hero is full-bleed, the propose panel is narrow) rather than the equal-
 * card-row template a 6-item feature list defaults to.
 */
export function Section({
  id,
  eyebrow,
  title,
  weight = "normal",
  children,
}: {
  id: string
  eyebrow: string
  title: string
  weight?: "hero" | "normal" | "compact"
  children: ReactNode
}) {
  return (
    <section
      id={id}
      className={
        weight === "hero"
          ? "mx-auto max-w-5xl px-6 py-20 md:px-10"
          : weight === "compact"
            ? "mx-auto max-w-3xl px-6 py-12 md:px-10"
            : "mx-auto max-w-5xl px-6 py-14 md:px-10"
      }
    >
      <div className="mb-6 flex items-baseline gap-3 border-b border-wire-rule pb-3">
        <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-wire-muted">
          {eyebrow}
        </span>
      </div>
      <h2
        className={
          weight === "hero"
            ? "mb-8 text-3xl font-medium tracking-tight text-wire-ink md:text-4xl"
            : "mb-6 text-xl font-medium tracking-tight text-wire-ink"
        }
      >
        {title}
      </h2>
      {children}
    </section>
  )
}
