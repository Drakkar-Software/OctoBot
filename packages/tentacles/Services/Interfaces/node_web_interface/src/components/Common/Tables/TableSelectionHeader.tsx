import { CenteredCellContent } from "@/components/Common/Tables/CenteredCellContent"
import { Checkbox } from "@/components/ui/checkbox"
import { TableHead } from "@/components/ui/table"

type TableSelectionHeaderProps = {
  visibleIds: string[]
  selectedIds: Set<string>
  onToggleAllVisible: (ids: string[], select: boolean) => void
}

export function TableSelectionHeader({
  visibleIds,
  selectedIds,
  onToggleAllVisible,
}: TableSelectionHeaderProps) {
  const selectedVisibleCount = visibleIds.filter((id) =>
    selectedIds.has(id),
  ).length
  const allVisibleSelected =
    visibleIds.length > 0 && selectedVisibleCount === visibleIds.length
  const someVisibleSelected =
    selectedVisibleCount > 0 && selectedVisibleCount < visibleIds.length

  return (
    <TableHead className="w-10 text-center">
      <CenteredCellContent>
        <Checkbox
          aria-label="Select all visible rows"
          checked={
            allVisibleSelected
              ? true
              : someVisibleSelected
                ? "indeterminate"
                : false
          }
          disabled={visibleIds.length === 0}
          onCheckedChange={() => {
            onToggleAllVisible(visibleIds, !allVisibleSelected)
          }}
        />
      </CenteredCellContent>
    </TableHead>
  )
}
