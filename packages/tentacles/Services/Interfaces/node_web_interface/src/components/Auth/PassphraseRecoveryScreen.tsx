import { useMutation, useQuery } from "@tanstack/react-query"
import { Link, useNavigate } from "@tanstack/react-router"
import { ShieldCheck, TriangleAlert } from "lucide-react"
import { useMemo, useState } from "react"

import { type WalletInfo, WalletsService } from "@/client"
import { AuthLayout } from "@/components/Common/AuthLayout"
import { LoadingButton } from "@/components/ui/loading-button"
import { PasswordInput } from "@/components/ui/password-input"
import useCustomToast from "@/hooks/useCustomToast"
import { markLoginPassphraseRecovered } from "@/lib/login-passphrase-recovered-hint"
import {
  RecoverPassphraseApiError,
  recoverWalletPassphrase,
} from "@/lib/recover-passphrase-api"
import { truncateAddress } from "@/lib/wallet-utils"

type RecoveryMaterialMode = "seed" | "private_key"

export function PassphraseRecoveryScreen() {
  const navigate = useNavigate()
  const { showErrorToast } = useCustomToast()
  const [materialMode, setMaterialMode] = useState<RecoveryMaterialMode>("seed")
  const [seed, setSeed] = useState("")
  const [privateKey, setPrivateKey] = useState("")
  const [newPassphrase, setNewPassphrase] = useState("")
  const [confirmPassphrase, setConfirmPassphrase] = useState("")
  const [selectedWallet, setSelectedWallet] = useState<WalletInfo | null>(null)
  const [error, setError] = useState<string | null>(null)

  const {
    data: wallets = [],
    isPending: walletsLoading,
    isError: walletsError,
  } = useQuery({
    queryKey: ["wallets"],
    queryFn: () => WalletsService.listWallets(),
    staleTime: 0,
  })

  const multiWallet = !walletsLoading && wallets.length > 1
  const isPrivateKeyValid = /^(0x)?[0-9a-fA-F]{64}$/.test(privateKey.trim())
  const isSeedValid = seed.trim().split(/\s+/).length >= 12
  const passphrasesMatch =
    newPassphrase.length >= 8 && newPassphrase === confirmPassphrase

  const materialValid =
    materialMode === "seed"
      ? isSeedValid
      : isPrivateKeyValid

  const targetAddress = useMemo(() => {
    if (multiWallet) {
      return selectedWallet?.address ?? null
    }
    if (wallets.length === 1) {
      return wallets[0].address
    }
    return null
  }, [multiWallet, selectedWallet, wallets])

  const mutation = useMutation({
    mutationFn: () =>
      recoverWalletPassphrase({
        new_passphrase: newPassphrase,
        address: targetAddress,
        seed: materialMode === "seed" ? seed.trim() : null,
        private_key:
          materialMode === "private_key" ? privateKey.trim() : null,
      }),
    onSuccess: () => {
      markLoginPassphraseRecovered()
      navigate({ to: "/login" })
    },
    onError: (err: unknown) => {
      if (err instanceof RecoverPassphraseApiError && err.status === 503) {
        showErrorToast(
          "Passphrase recovery is unavailable on this node. Contact your operator if you need help.",
        )
        return
      }
      setError(
        err instanceof Error ? err.message : "Could not reset your passphrase.",
      )
    },
  })

  if (walletsError) {
    return (
      <AuthLayout>
        <div className="flex flex-col items-center gap-2 text-center">
          <h1 className="text-2xl font-bold">Unable to connect</h1>
          <p className="text-sm text-muted-foreground">
            Could not reach the node. Please check your connection and reload.
          </p>
        </div>
      </AuthLayout>
    )
  }

  if (multiWallet && selectedWallet === null) {
    return (
      <AuthLayout>
        <div className="flex flex-col gap-6">
          <div className="flex flex-col items-center gap-2 text-center">
            <h1 className="text-2xl font-bold">Recover passphrase</h1>
            <p className="text-sm text-muted-foreground">
              Choose the wallet you want to reset.
            </p>
          </div>
          <div className="flex flex-col gap-2">
            {wallets.map((wallet) => (
              <button
                key={wallet.address}
                type="button"
                onClick={() => setSelectedWallet(wallet)}
                className="flex items-center gap-3 rounded-lg border p-4 text-left transition-colors hover:bg-muted"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium truncate">
                      {wallet.name || (
                        <span className="text-muted-foreground italic font-normal">
                          No name
                        </span>
                      )}
                    </span>
                    {wallet.is_admin && (
                      <ShieldCheck className="size-4 shrink-0 text-primary" />
                    )}
                  </div>
                  <span className="text-xs text-muted-foreground font-mono">
                    {truncateAddress(wallet.address)}
                  </span>
                </div>
              </button>
            ))}
          </div>
          <Link
            to="/login"
            className="text-center text-xs text-muted-foreground underline underline-offset-2"
          >
            Back to log in
          </Link>
        </div>
      </AuthLayout>
    )
  }

  const submitDisabled =
    !materialValid ||
    !passphrasesMatch ||
    !targetAddress ||
    mutation.isPending

  return (
    <AuthLayout>
      <form
        className="flex flex-col gap-6"
        onSubmit={(event) => {
          event.preventDefault()
          setError(null)
          if (submitDisabled) return
          mutation.mutate()
        }}
      >
        <div className="flex flex-col items-center gap-2 text-center">
          <h1 className="text-2xl font-bold">Recover passphrase</h1>
          <p className="text-sm text-muted-foreground">
            Prove you own this wallet with your saved seed phrase or private key,
            then set a new passphrase.
          </p>
          {multiWallet && selectedWallet ? (
            <button
              type="button"
              onClick={() => setSelectedWallet(null)}
              className="text-xs text-muted-foreground underline underline-offset-2"
            >
              Choose a different wallet
            </button>
          ) : null}
        </div>

        <div className="flex items-start gap-2 rounded-md border border-warn/30 bg-warn/10 p-3 text-sm text-warn">
          <TriangleAlert className="mt-0.5 size-4 shrink-0" />
          <span>
            This replaces your wallet passphrase. Keep your seed phrase or private
            key offline. Anyone with that backup can reset access again.
          </span>
        </div>

        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => {
              setMaterialMode("seed")
              setError(null)
            }}
            className={`flex-1 rounded-md border px-3 py-1.5 text-sm font-medium transition-colors ${materialMode === "seed" ? "bg-primary text-primary-foreground" : "hover:bg-accent"}`}
          >
            Seed phrase
          </button>
          <button
            type="button"
            onClick={() => {
              setMaterialMode("private_key")
              setError(null)
            }}
            className={`flex-1 rounded-md border px-3 py-1.5 text-sm font-medium transition-colors ${materialMode === "private_key" ? "bg-primary text-primary-foreground" : "hover:bg-accent"}`}
          >
            Private key
          </button>
        </div>

        {materialMode === "seed" ? (
          <div className="flex flex-col gap-1">
            <label htmlFor="recovery-seed" className="text-sm font-medium">
              Seed phrase
            </label>
            <textarea
              id="recovery-seed"
              data-testid="recovery-seed-input"
              className="min-h-24 rounded-md border bg-background px-3 py-2 text-sm"
              value={seed}
              onChange={(event) => {
                setSeed(event.target.value)
                setError(null)
              }}
              placeholder="Enter your 12 or 24 word seed phrase"
              autoComplete="off"
            />
          </div>
        ) : (
          <div className="flex flex-col gap-1">
            <label htmlFor="recovery-private-key" className="text-sm font-medium">
              Private key
            </label>
            <PasswordInput
              id="recovery-private-key"
              data-testid="recovery-private-key-input"
              value={privateKey}
              onChange={(event) => {
                setPrivateKey(event.target.value)
                setError(null)
              }}
              placeholder="64-character hex private key"
              autoComplete="off"
            />
          </div>
        )}

        <div className="flex flex-col gap-1">
          <label htmlFor="recovery-new-passphrase" className="text-sm font-medium">
            New passphrase
          </label>
          <PasswordInput
            id="recovery-new-passphrase"
            data-testid="recovery-new-passphrase-input"
            value={newPassphrase}
            onChange={(event) => {
              setNewPassphrase(event.target.value)
              setError(null)
            }}
            placeholder="At least 8 characters"
            autoComplete="new-password"
          />
        </div>

        <div className="flex flex-col gap-1">
          <label
            htmlFor="recovery-confirm-passphrase"
            className="text-sm font-medium"
          >
            Confirm new passphrase
          </label>
          <PasswordInput
            id="recovery-confirm-passphrase"
            data-testid="recovery-confirm-passphrase-input"
            value={confirmPassphrase}
            onChange={(event) => {
              setConfirmPassphrase(event.target.value)
              setError(null)
            }}
            placeholder="Repeat your new passphrase"
            autoComplete="new-password"
          />
        </div>

        {error ? (
          <p className="text-sm text-destructive" data-testid="recovery-error">
            {error}
          </p>
        ) : null}

        <LoadingButton type="submit" loading={mutation.isPending} disabled={submitDisabled}>
          Reset passphrase
        </LoadingButton>

        <Link
          to="/login"
          className="text-center text-xs text-muted-foreground underline underline-offset-2"
        >
          Back to log in
        </Link>
      </form>
    </AuthLayout>
  )
}
