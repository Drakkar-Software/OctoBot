import { truncateAddress } from "@/lib/wallet-utils"

export type RecoverWalletIdentityHeaderProps = {
  address: string
  walletName?: string | null
  walletNamePending?: boolean
}

export function RecoverWalletIdentityHeader({
  address,
  walletName,
  walletNamePending = false,
}: RecoverWalletIdentityHeaderProps) {
  const trimmedName = walletName?.trim()

  return (
    <div className="flex flex-col items-center gap-0.5 text-center">
      <div
        className="min-h-6 flex items-center justify-center"
        data-testid="recover-wallet-name"
        aria-busy={walletNamePending ? true : undefined}
        data-wallet-name-pending={walletNamePending ? "true" : undefined}
      >
        {walletNamePending ? (
          <span className="font-medium invisible" aria-hidden="true">
            {"\u00a0"}
          </span>
        ) : trimmedName ? (
          <span className="font-medium truncate max-w-full">{trimmedName}</span>
        ) : (
          <span className="text-muted-foreground italic font-normal">
            No name
          </span>
        )}
      </div>
      <span
        className="text-xs text-muted-foreground font-mono"
        data-testid="recover-wallet-address"
      >
        {truncateAddress(address)}
      </span>
    </div>
  )
}
