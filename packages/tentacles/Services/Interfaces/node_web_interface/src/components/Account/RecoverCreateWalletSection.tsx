import { Link, useNavigate } from "@tanstack/react-router"

import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { START_FRESH_FROM_RECOVER_KEY } from "@/lib/setup-guard"

export function RecoverCreateWalletSection() {
  const navigate = useNavigate()

  const startCreateWallet = () => {
    sessionStorage.setItem(START_FRESH_FROM_RECOVER_KEY, "1")
    void navigate({ to: "/setup" })
  }

  return (
    <div className="flex flex-col gap-4" data-testid="recover-create-wallet-section">
      <div className="relative">
        <Separator />
        <span
          className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-background px-2 text-xs text-muted-foreground"
        >
          Or
        </span>
      </div>
      <div className="flex flex-col gap-2 rounded-lg border bg-muted/30 p-4 text-center">
        <p className="font-medium">Create a new wallet</p>
        <p className="text-sm text-muted-foreground">
          Start fresh on this node. This is not account recovery — you will not
          get back into an existing wallet without its recovery phrase.
        </p>
        <Button
          type="button"
          variant="outline"
          className="w-full"
          data-testid="recover-create-wallet-button"
          onClick={startCreateWallet}
        >
          Set up a new wallet
        </Button>
        <p className="text-xs text-muted-foreground">
          Already have a wallet here?{" "}
          <Link to="/login" className="underline underline-offset-2 hover:text-foreground">
            Back to unlock
          </Link>
        </p>
      </div>
    </div>
  )
}
