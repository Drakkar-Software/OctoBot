import { useQuery, useQueryClient } from "@tanstack/react-query"
import { Bug, ScrollText } from "lucide-react"
import { useCallback, useEffect, useMemo, useRef, useState } from "react"

import { type ApiError, type DebugState, WalletsService } from "@/client"
import {
  DebugExecuteActionDialogHost,
  type DebugExecuteActionHandle,
} from "@/components/Debug/DebugExecuteActionDialogHost"
import { DebugSchedulerWarning } from "@/components/Debug/DebugSchedulerWarning"
import { DebugTabsPanel } from "@/components/Debug/DebugTabsPanel"
import { DebugToolbar } from "@/components/Debug/DebugToolbar"
import { DownloadLogsDialog } from "@/components/Debug/dialogs/DownloadLogsDialog"
import { ImportDebugStateDialog } from "@/components/Debug/dialogs/ImportDebugStateDialog"
import { ImportedDebugSnapshotBanner } from "@/components/Debug/ImportedDebugSnapshotBanner"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import useAuth from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import {
  buildDebugExportFilename,
  downloadDebugStateJson,
  summarizeImportedDebugState,
} from "@/lib/debug/import"
import { getDebugQueryOptions } from "@/lib/debug/queries"
import type { ExecuteActionDraft } from "@/lib/debug/types"
import { handleError } from "@/utils"

export function DebugView() {
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const { showErrorToast, showSuccessToast } = useCustomToast()
  const currentAddress = localStorage.getItem("auth_username") ?? ""
  const isSuperuser = user?.is_superuser === true

  const [walletAddress, setWalletAddress] = useState(currentAddress)
  const [importOpen, setImportOpen] = useState(false)
  const [downloadLogsOpen, setDownloadLogsOpen] = useState(false)
  const [importedSnapshot, setImportedSnapshot] = useState<DebugState | null>(
    null,
  )
  const [importMeta, setImportMeta] = useState<{
    importedAt: Date
    sourceLabel: string
  } | null>(null)

  const executeActionRef = useRef<DebugExecuteActionHandle>(null)
  const openExecuteAction = useCallback((draft?: ExecuteActionDraft) => {
    executeActionRef.current?.open(draft)
  }, [])

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

  const showTabsPanel =
    isImportedMode || (!schedulerUnavailable && !debugQuery.isLoading)

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Bug className="size-6" />
            Debug view
          </h1>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setDownloadLogsOpen(true)}
            >
              <ScrollText className="size-4" />
              Download logs
            </Button>
            <Separator orientation="vertical" className="h-6" />
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
              onExecute={() => openExecuteAction()}
            />
          </div>
        </div>
        <p className="text-muted-foreground text-sm">
          Snapshot of current and historical activity. Contains no API secret or
          private keys.
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

      {showTabsPanel && (
        <DebugTabsPanel
          isImportedMode={isImportedMode}
          walletQueryParam={walletQueryParam}
          automations={automations}
          userActions={userActions}
          accounts={accounts}
          exchangeConfigs={exchangeConfigs}
          accountTradings={accountTradings}
          localStrategies={localStrategies}
          onRefresh={refresh}
          onOpenExecuteAction={openExecuteAction}
        />
      )}

      <ImportDebugStateDialog
        open={importOpen}
        onOpenChange={setImportOpen}
        onImported={handleImported}
      />

      <DownloadLogsDialog
        open={downloadLogsOpen}
        onOpenChange={setDownloadLogsOpen}
        automations={automations}
      />

      <DebugExecuteActionDialogHost
        ref={executeActionRef}
        walletAddress={walletQueryParam}
        onSuccess={refresh}
        copyOnly={isImportedMode}
      />
    </div>
  )
}
