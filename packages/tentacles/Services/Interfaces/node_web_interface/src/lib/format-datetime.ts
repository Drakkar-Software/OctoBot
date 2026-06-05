export const DATE_TIME_FORMATTER = new Intl.DateTimeFormat(undefined, {
  year: "2-digit",
  month: "numeric",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
  second: "2-digit",
})

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—"
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : DATE_TIME_FORMATTER.format(date)
}
