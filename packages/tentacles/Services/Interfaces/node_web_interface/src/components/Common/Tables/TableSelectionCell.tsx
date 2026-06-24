import { CenteredCellContent } from "@/components/Common/Tables/CenteredCellContent"
import { Checkbox } from "@/components/ui/checkbox"
import { TableCell } from "@/components/ui/table"
import { debugTableCellClass } from "@/lib/debug/display-utils"

type TableSelectionCellProps = {
  rowId: string
  selected: boolean
  onToggleRow: (id: string) => void
}

export function TableSelectionCell({
  rowId,
  selected,
  onToggleRow,
}: TableSelectionCellProps) {
  return (
    <TableCell className={debugTableCellClass("center", "w-10")}>
      <CenteredCellContent>
        <Checkbox
          aria-label={`Select row ${rowId}`}
          checked={selected}
          onCheckedChange={() => onToggleRow(rowId)}
        />
      </CenteredCellContent>
    </TableCell>
  )
}
