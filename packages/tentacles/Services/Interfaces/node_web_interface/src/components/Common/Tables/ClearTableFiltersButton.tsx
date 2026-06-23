type ClearTableFiltersButtonProps = {
  onClear: () => void
}

export function ClearTableFiltersButton({
  onClear,
}: ClearTableFiltersButtonProps) {
  return (
    <div className="flex justify-end mb-2">
      <button
        type="button"
        className="text-xs text-muted-foreground hover:text-foreground hover:underline"
        onClick={onClear}
      >
        Clear filters
      </button>
    </div>
  )
}
