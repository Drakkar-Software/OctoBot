import { useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { Bug } from "lucide-react"
import { useEffect, useMemo, useState } from "react"

import {
  type ApiError,
  type DebugState,
  WalletsService,
} from "@/client"
import { DebugSchedulerWarning } from "@/components/Debug/DebugSchedulerWarning"
import { DebugToolbar } from "@/components/Debug/DebugToolbar"
import { ExecuteActionDialog } from "@/components/Debug/dialogs/ExecuteActionDialog"
import { ImportDebugStateDialog } from "@/components/Debug/dialogs/ImportDebugStateDialog"
import { ImportedDebugSnapshotBanner } from "@/components/Debug/ImportedDebugSnapshotBanner"
import { AccountsTable } from "@/components/Debug/tables/AccountsTable"
import { AutomationsTable } from "@/components/Debug/tables/AutomationsTable"
import { ExchangeConfigsTable } from "@/components/Debug/tables/ExchangeConfigsTable"
import { StrategiesTable } from "@/components/Debug/tables/StrategiesTable"
import { UserActionsTable } from "@/components/Debug/tables/UserActionsTable"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import useAuth from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import {
  buildDebugExportFilename,
  downloadDebugStateJson,
  summarizeImportedDebugState,
} from "@/lib/debug/import"
import { getDebugQueryOptions } from "@/lib/debug/queries"
import type { ExecuteActionDraft } from "@/lib/debug/types"
import {
  buildAccountEditUserActionJson,
  buildAutomationCreateUserActionJsonForAccount,
  buildAutomationCreateUserActionJsonForStrategy,
  buildAutomationSignalUserActionJson,
  buildAutomationStopUserActionJson,
  buildExchangeConfigEditUserActionJson,
  buildStrategyEditUserActionJson,
} from "@/lib/debug/user-action-templates"
import { handleError } from "@/utils"

function DebugPage() {
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const currentAddress = localStorage.getItem("auth_username") ?? ""
  const isSuperuser = user?.is_superuser === true

  const [walletAddress, setWalletAddress] = useState(currentAddress)
  const [executeOpen, setExecuteOpen] = useState(false)
  const [executeDraft, setExecuteDraft] = useState<ExecuteActionDraft | null>(
    null,
  )
  const [importOpen, setImportOpen] = useState(false)
  const [importedSnapshot, setImportedSnapshot] = useState<DebugState | null>(
    null,
  )
  const [importMeta, setImportMeta] = useState<{
    importedAt: Date
    sourceLabel: string
  } | null>(null)

  const openExecuteDialog = (draft?: ExecuteActionDraft) => {
    setExecuteDraft(draft ?? null)
    setExecuteOpen(true)
  }

  const handleExecuteOpenChange = (open: boolean) => {
    setExecuteOpen(open)
    if (!open) {
      setExecuteDraft(null)
    }
  }

  useEffect(() => {
    if (!isSuperuser) setWalletAddress(currentAddress)
  }, [currentAddress, isSuperuser])

  const walletQueryParam = useMemo(() => {
    if (!isSuperuser || !walletAddress) return undefined
    if (walletAddress.toLowerCase() === currentAddress.toLowerCase()) {
      return undefined
    }
    return walletAddress
  }, [isSuperuser, walletAddress, currentAddress])

  const { data: wallets = [] } = useQuery({
    queryKey: ["wallets"],
    queryFn: () => WalletsService.listWallets(),
    enabled: isSuperuser,
  })

  const isImportedMode = importedSnapshot !== null

  const debugQuery = useQuery({
    ...getDebugQueryOptions(walletQueryParam),
    enabled: !isImportedMode,
    retry: (failureCount, error) => {
      const status = (error as ApiError)?.status
      if (status === 503) return false
      return failureCount < 2
    },
  })

  useEffect(() => {
    if (
      !isImportedMode &&
      debugQuery.isError &&
      debugQuery.error &&
      (debugQuery.error as ApiError).status !== 503
    ) {
      handleError.bind(showErrorToast)(debugQuery.error as ApiError)
    }
  }, [isImportedMode, debugQuery.isError, debugQuery.error, showErrorToast])

  const activeDebugState = isImportedMode ? importedSnapshot : debugQuery.data

  const automations = activeDebugState?.debug?.automations ?? []
  const userActions = activeDebugState?.debug?.user_actions ?? []
  const accounts = activeDebugState?.debug?.accounts ?? []
  const exchangeConfigs = activeDebugState?.debug?.exchange_configs ?? []
  const accountTradings = activeDebugState?.debug?.account_tradings ?? []
  const localStrategies = activeDebugState?.debug?.local_strategies ?? []
  const schedulerUnavailable =
    !isImportedMode &&
    debugQuery.isError &&
    (debugQuery.error as ApiError)?.status === 503

  const importedSummary = useMemo(() => {
    if (!importedSnapshot || !importMeta) return null
    return summarizeImportedDebugState(importedSnapshot, importMeta)
  }, [importedSnapshot, importMeta])

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ["debug"] })
  }

  const handleImported = (state: DebugState, sourceLabel: string) => {
    setImportedSnapshot(state)
    setImportMeta({ importedAt: new Date(), sourceLabel })
  }

  const returnToLiveView = () => {
    setImportedSnapshot(null)
    setImportMeta(null)
  }

  const handleExportSnapshot = () => {
    if (!debugQuery.data) return
    const exportWallet =
      walletAddress.trim().length > 0 ? walletAddress : currentAddress
    downloadDebugStateJson(
      debugQuery.data,
      buildDebugExportFilename(exportWallet),
    )
    showSuccessToast("Debug snapshot downloaded")
  }

  const canExportSnapshot =
    !isImportedMode && Boolean(debugQuery.data) && !schedulerUnavailable

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Bug className="size-6" />
            Debug view
          </h1>
          <DebugToolbar
            isImportedMode={isImportedMode}
            isSuperuser={isSuperuser}
            wallets={wallets}
            walletAddress={walletAddress}
            onWalletAddressChange={setWalletAddress}
            onImport={() => setImportOpen(true)}
            onReturnToLive={returnToLiveView}
            onExport={handleExportSnapshot}
            canExportSnapshot={canExportSnapshot}
            onRefresh={refresh}
            onExecute={() => openExecuteDialog()}
          />
        </div>
        <p className="text-muted-foreground text-sm">
          Snapshot of current and historical activity. Contains no API secret
          or private keys.
          {activeDebugState?.version && (
            <span className="ml-2 font-mono text-xs">
              state v{activeDebugState.version}
            </span>
          )}
        </p>
      </div>

      {importedSummary && (
        <ImportedDebugSnapshotBanner
          summary={importedSummary}
          onReturnToLive={returnToLiveView}
        />
      )}

      {schedulerUnavailable && <DebugSchedulerWarning />}

      {!isImportedMode && debugQuery.isLoading && !schedulerUnavailable && (
        <p className="text-sm text-muted-foreground">Loading debug state…</p>
      )}

      {(isImportedMode || (!schedulerUnavailable && !debugQuery.isLoading)) && (
        <Tabs defaultValue="automations">
          <TabsList className="flex h-auto flex-wrap gap-1">
            <TabsTrigger value="automations">
              Automations ({automations.length})
            </TabsTrigger>
            <TabsTrigger value="user-actions">
              User actions ({userActions.length})
            </TabsTrigger>
            <TabsTrigger value="accounts">
              Accounts ({accounts.length})
            </TabsTrigger>
            <TabsTrigger value="exchange-configs">
              Exchange configs ({exchangeConfigs.length})
            </TabsTrigger>
            <TabsTrigger value="strategies">
              Strategies ({localStrategies.length})
            </TabsTrigger>
          </TabsList>
          <TabsContent value="automations" className="mt-4">
            <AutomationsTable
              rows={automations}
              readOnly={isImportedMode}
              walletAddress={isImportedMode ? undefined : walletQueryParam}
              accountTradings={accountTradings}
              onSuccess={isImportedMode ? undefined : refresh}
              onSignal={
                isImportedMode
                  ? (automation) =>
                      openExecuteDialog({
                        actionType: "automation_signal",
                        jsonText: buildAutomationSignalUserActionJson(
                          automation.id,
                        ),
                      })
                  : undefined
              }
              onStop={(automation) =>
                openExecuteDialog({
                  actionType: "automation_stop",
                  jsonText: buildAutomationStopUserActionJson(automation.id),
                })
              }
            />
          </TabsContent>
          <TabsContent value="user-actions" className="mt-4">
            <UserActionsTable rows={userActions} />
          </TabsContent>
          <TabsContent value="accounts" className="mt-4">
            <AccountsTable
              rows={accounts}
              exchangeConfigs={exchangeConfigs}
              accountTradings={accountTradings}
              onEdit={(account) =>
                openExecuteDialog({
                  actionType: "account_edit",
                  jsonText: buildAccountEditUserActionJson(account),
                })
              }
              onStartAutomation={(account) =>
                openExecuteDialog({
                  actionType: "automation_create",
                  jsonText: buildAutomationCreateUserActionJsonForAccount(
                    account,
                  ),
                })
              }
            />
          </TabsContent>
          <TabsContent value="exchange-configs" className="mt-4">
            <ExchangeConfigsTable
              rows={exchangeConfigs}
              accounts={accounts}
              onEdit={(config) =>
                openExecuteDialog({
                  actionType: "exchange_config_edit",
                  jsonText: buildExchangeConfigEditUserActionJson(config),
                })
              }
            />
          </TabsContent>
          <TabsContent value="strategies" className="mt-4">
            <StrategiesTable
              rows={localStrategies}
              onEdit={(strategy) =>
                openExecuteDialog({
                  actionType: "strategy_edit",
                  jsonText: buildStrategyEditUserActionJson(strategy),
                })
              }
              onStartAutomation={(strategy) =>
                openExecuteDialog({
                  actionType: "automation_create",
                  jsonText: buildAutomationCreateUserActionJsonForStrategy(
                    strategy,
                  ),
                })
              }
            />
          </TabsContent>
        </Tabs>
      )}

      <ImportDebugStateDialog
        open={importOpen}
        onOpenChange={setImportOpen}
        onImported={handleImported}
      />

      <ExecuteActionDialog
        open={executeOpen}
        onOpenChange={handleExecuteOpenChange}
        walletAddress={walletQueryParam}
        onSuccess={refresh}
        draft={executeDraft}
        copyOnly={isImportedMode}
      />
    </div>
  )
}

export const Route = createFileRoute("/_layout/debug")({
  component: DebugPage,
  head: () => ({
    meta: [{ title: "Debug view" }],
  }),
})
