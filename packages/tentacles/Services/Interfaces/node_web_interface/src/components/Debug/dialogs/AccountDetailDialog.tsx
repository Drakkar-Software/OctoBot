import { useQuery } from "@tanstack/react-query"
import { useMemo } from "react"

import type { Account, ExchangeConfig } from "@/client"
import { PortfolioHistoryChart } from "@/components/Debug/PortfolioHistoryChart"
import { CollapsibleJsonView } from "@/components/ui/collapsible-json-view"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { getAccountHistoricalValuesQueryOptions } from "@/lib/debug/queries"
import { getNegativeHoldingsWarnings } from "@/lib/debug/portfolio-history-warnings"

type AccountDetailDialogProps = {
  account: Account | null
  open: boolean
  onOpenChange: (open: boolean) => void
  walletQueryParam?: string
  isImportedMode?: boolean
  exchangeConfigs?: ExchangeConfig[]
}

export function AccountDetailDialog({
  account,
  open,
  onOpenChange,
  walletQueryParam,
  isImportedMode = false,
  exchangeConfigs = [],
}: AccountDetailDialogProps) {
  const historyQuery = useQuery({
    ...getAccountHistoricalValuesQueryOptions(
      account?.id,
      walletQueryParam,
      open && !isImportedMode,
    ),
  })

  const negativeHoldingsWarnings = useMemo(
    () =>
      getNegativeHoldingsWarnings(
        historyQuery.data,
        historyQuery.data?.history?.unit ?? "USDT",
        account,
        exchangeConfigs,
      ),
    [account, exchangeConfigs, historyQuery.data],
  )

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[85vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>{account?.name ?? "Account"}</DialogTitle>
          <DialogDescription>
            Portfolio history and full JSON payload
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 overflow-y-auto min-h-0">
          <PortfolioHistoryChart
            state={historyQuery.data}
            isLoading={historyQuery.isLoading}
            error={historyQuery.error}
            isImportedMode={isImportedMode}
          />
          {negativeHoldingsWarnings.length > 0 ? (
            <div className="rounded-md border border-amber-500/40 bg-amber-500/10 p-3 text-sm text-amber-900 dark:text-amber-100">
              <p className="font-medium">Negative holdings detected in history</p>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                {negativeHoldingsWarnings.map((warning) => (
                  <li key={warning.symbol}>
                    {warning.symbol} has negative holdings. Add{" "}
                    <span className="font-mono">{warning.suggestedTradeSymbol}</span> to{" "}
                    <span className="font-mono">historical_trade_symbols</span>
                    {warning.exchangeConfigLabel
                      ? ` on exchange config "${warning.exchangeConfigLabel}".`
                      : " on the linked exchange config."}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          {account != null ? (
            <CollapsibleJsonView value={account} />
          ) : (
            <p className="text-sm text-muted-foreground">—</p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
