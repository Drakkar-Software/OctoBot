import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { TriangleAlert } from "lucide-react"
import { useMemo, useState } from "react"

import { ExportWalletDialog } from "@/components/Settings/WalletManagement/ExportWalletDialog"
import { Checkbox } from "@/components/ui/checkbox"
import { LoadingButton } from "@/components/ui/loading-button"
import useAuth from "@/hooks/useAuth"
import { isWalletBackupPromptEligible } from "@/lib/wallet-backup-prompt"
import {
  acknowledgeWalletBackupSaved,
  fetchWalletBackupPromptStatus,
} from "@/lib/wallet-backup-prompt-api"
import {
  loadLocalWalletBackupSavedAck,
  loadLocalWalletSetupSucceededAtMs,
  saveLocalWalletBackupSavedAck,
} from "@/lib/wallet-backup-prompt-storage"

export function WalletBackupPromptBanner() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [savedChecked, setSavedChecked] = useState(false)

  const statusQuery = useQuery({
    queryKey: ["wallet-backup-prompt-status"],
    queryFn: async () => {
      const [remote, localSetupAtMs, localAck] = await Promise.all([
        fetchWalletBackupPromptStatus(),
        loadLocalWalletSetupSucceededAtMs(),
        loadLocalWalletBackupSavedAck(),
      ])
      const setupSucceededAtMs =
        remote.wallet_setup_succeeded_at != null
          ? remote.wallet_setup_succeeded_at * 1000
          : localSetupAtMs
      return {
        setupSucceededAtMs,
        backupSavedAck:
          remote.backup_saved_ack || localAck,
      }
    },
  })

  const ackMutation = useMutation({
    mutationFn: async () => {
      await acknowledgeWalletBackupSaved()
      await saveLocalWalletBackupSavedAck()
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["wallet-backup-prompt-status"] })
    },
  })

  const eligible = useMemo(() => {
    if (!statusQuery.data) {
      return false
    }
    return isWalletBackupPromptEligible({
      setupSucceededAtMs: statusQuery.data.setupSucceededAtMs,
      nowMs: Date.now(),
      backupSavedAck: statusQuery.data.backupSavedAck,
    })
  }, [statusQuery.data])

  if (!eligible || !user?.email) {
    return null
  }

  return (
    <div
      className="mb-6 rounded-lg border border-warn/30 bg-warn/10 p-4"
      data-testid="wallet-backup-prompt-banner"
    >
      <div className="flex items-start gap-3">
        <TriangleAlert className="mt-0.5 size-5 shrink-0 text-warn" />
        <div className="flex flex-1 flex-col gap-3">
          <div>
            <p className="font-medium text-foreground">Save your wallet backup</p>
            <p className="text-sm text-muted-foreground">
              Export your seed phrase or private key and store it offline. You can
              use it on the log in page to reset your passphrase if you forget it.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <ExportWalletDialog
              walletAddress={user.email}
              isOwnWallet={true}
              showTextTrigger={true}
            />
            <label className="flex items-center gap-2 text-sm">
              <Checkbox
                checked={savedChecked}
                onCheckedChange={(checked) => setSavedChecked(checked === true)}
                data-testid="wallet-backup-saved-checkbox"
              />
              I saved it
            </label>
            <LoadingButton
              type="button"
              variant="outline"
              size="sm"
              loading={ackMutation.isPending}
              disabled={!savedChecked}
              onClick={() => ackMutation.mutate()}
            >
              Dismiss
            </LoadingButton>
          </div>
        </div>
      </div>
    </div>
  )
}
