type ColumnFilterInputProps = {
  value: string
  onChange: (value: string) => void
  placeholder?: string
}

export function ColumnFilterInput({
  value,
  onChange,
  placeholder = "Filter…",
}: ColumnFilterInputProps) {
  return (
    <input
      type="text"
      value={value}
      onChange={(event) => onChange(event.target.value)}
      placeholder={placeholder}
      className="mt-1.5 h-7 w-full min-w-0 rounded border border-rule bg-input px-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-frost"
    />
  )
}
