import { useQuery } from "@tanstack/react-query"
import { useMemo, useState } from "react"

import type { Account } from "@/client"
import { PortfolioHistoryChart } from "@/components/Debug/PortfolioHistoryChart"
import { CopyableIdCell } from "@/components/Common/Tables/CopyableIdCell"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { getAggregatedAccountHistoricalValuesQueryOptions } from "@/lib/debug/queries"

type AccountsHistoryDialogProps = {
  accounts: Account[]
  open: boolean
  onOpenChange: (open: boolean) => void
  walletQueryParam?: string
  isImportedMode?: boolean
}

type AccountsHistoryTabProps = {
  accounts: Account[]
  isSimulated: boolean
  isActive: boolean
  dialogOpen: boolean
  walletQueryParam?: string
  isImportedMode: boolean
}

function AccountsHistoryTab({
  accounts,
  isSimulated,
  isActive,
  dialogOpen,
  walletQueryParam,
  isImportedMode,
}: AccountsHistoryTabProps) {
  const tabAccounts = useMemo(
    () => accounts.filter((account) => account.is_simulated === isSimulated),
    [accounts, isSimulated],
  )
  const historyQuery = useQuery({
    ...getAggregatedAccountHistoricalValuesQueryOptions(
      isSimulated,
      walletQueryParam,
      dialogOpen && isActive && !isImportedMode,
    ),
  })

  return (
    <div className="space-y-4">
      <PortfolioHistoryChart
        state={historyQuery.data}
        isLoading={historyQuery.isLoading}
        error={historyQuery.error}
        isImportedMode={isImportedMode}
      />
      <div className="space-y-2">
        <p className="text-sm font-medium">
          Accounts ({tabAccounts.length})
        </p>
        {tabAccounts.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No {isSimulated ? "simulated" : "real"} accounts.
          </p>
        ) : (
          <ul className="divide-y rounded-md border">
            {tabAccounts.map((account) => (
              <li
                key={account.id}
                className="flex items-center justify-between gap-3 px-3 py-2 text-sm"
              >
                <span className="truncate font-medium">{account.name}</span>
                <CopyableIdCell id={account.id} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

export function AccountsHistoryDialog({
  accounts,
  open,
  onOpenChange,
  walletQueryParam,
  isImportedMode = false,
}: AccountsHistoryDialogProps) {
  const [activeTab, setActiveTab] = useState<"real" | "simulated">("real")

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[85vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>Accounts history</DialogTitle>
          <DialogDescription>
            Aggregated portfolio value across all accounts of the selected type.
          </DialogDescription>
        </DialogHeader>
        <Tabs
          value={activeTab}
          onValueChange={(value) => setActiveTab(value as "real" | "simulated")}
          className="flex min-h-0 flex-1 flex-col"
        >
          <TabsList>
            <TabsTrigger value="real">Real</TabsTrigger>
            <TabsTrigger value="simulated">Simulated</TabsTrigger>
          </TabsList>
          <TabsContent value="real" className="mt-4 overflow-y-auto min-h-0">
            <AccountsHistoryTab
              accounts={accounts}
              isSimulated={false}
              isActive={activeTab === "real"}
              dialogOpen={open}
              walletQueryParam={walletQueryParam}
              isImportedMode={isImportedMode}
            />
          </TabsContent>
          <TabsContent value="simulated" className="mt-4 overflow-y-auto min-h-0">
            <AccountsHistoryTab
              accounts={accounts}
              isSimulated={true}
              isActive={activeTab === "simulated"}
              dialogOpen={open}
              walletQueryParam={walletQueryParam}
              isImportedMode={isImportedMode}
            />
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}
