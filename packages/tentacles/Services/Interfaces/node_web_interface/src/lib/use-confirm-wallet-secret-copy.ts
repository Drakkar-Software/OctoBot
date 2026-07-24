import { useCallback, useReducer } from "react"
import { toast } from "sonner"

export type WalletSecretType = "private_key" | "seed_phrase"

export type WalletSecretCopyState = {
  confirmOpen: boolean
  pendingSecret: string | null
  pendingSecretType: WalletSecretType
}

export type WalletSecretCopyAction =
  | { type: "request_copy"; secret: string; secretType: WalletSecretType }
  | { type: "open_change"; open: boolean }
  | { type: "confirm" }

export const initialWalletSecretCopyState: WalletSecretCopyState = {
  confirmOpen: false,
  pendingSecret: null,
  pendingSecretType: "private_key",
}

export function walletSecretCopyReducer(
  state: WalletSecretCopyState,
  action: WalletSecretCopyAction,
): WalletSecretCopyState {
  switch (action.type) {
    case "request_copy":
      return {
        confirmOpen: true,
        pendingSecret: action.secret,
        pendingSecretType: action.secretType,
      }
    case "open_change":
      if (action.open) {
        return { ...state, confirmOpen: true }
      }
      return initialWalletSecretCopyState
    case "confirm":
      return initialWalletSecretCopyState
  }
}

const WALLET_SECRET_COPY_DESCRIPTION: Record<WalletSecretType, string> = {
  private_key: "Private key",
  seed_phrase: "Seed phrase",
}

export async function performWalletSecretCopy(
  secret: string,
  secretType: WalletSecretType,
): Promise<void> {
  await navigator.clipboard.writeText(secret)
  toast.success("Copied to clipboard", {
    description: WALLET_SECRET_COPY_DESCRIPTION[secretType],
  })
}

type UseConfirmWalletSecretCopyOptions = {
  onCopied?: (secretType: WalletSecretType) => void
}

export function useConfirmWalletSecretCopy(
  options: UseConfirmWalletSecretCopyOptions = {},
) {
  const { onCopied } = options
  const [state, dispatch] = useReducer(
    walletSecretCopyReducer,
    initialWalletSecretCopyState,
  )

  const requestCopy = useCallback((secret: string, secretType: WalletSecretType) => {
    dispatch({ type: "request_copy", secret, secretType })
  }, [])

  const handleOpenChange = useCallback((open: boolean) => {
    dispatch({ type: "open_change", open })
  }, [])

  const handleConfirm = useCallback(() => {
    if (state.pendingSecret) {
      const secret = state.pendingSecret
      const secretType = state.pendingSecretType
      void performWalletSecretCopy(secret, secretType).then(() => {
        onCopied?.(secretType)
      })
    }
    dispatch({ type: "confirm" })
  }, [onCopied, state.pendingSecret, state.pendingSecretType])

  return {
    confirmOpen: state.confirmOpen,
    pendingSecretType: state.pendingSecretType,
    requestCopy,
    handleOpenChange,
    handleConfirm,
  }
}
