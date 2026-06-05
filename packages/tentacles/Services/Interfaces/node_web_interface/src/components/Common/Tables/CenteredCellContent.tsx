import type { ReactNode } from "react"

type CenteredCellContentProps = {
  children: ReactNode
}

export function CenteredCellContent({ children }: CenteredCellContentProps) {
  return <div className="flex justify-center">{children}</div>
}
