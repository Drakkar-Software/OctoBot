import { zodResolver } from "@hookform/resolvers/zod"
import { useQuery } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"
import { ShieldCheck } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { ApiError, type WalletInfo, WalletsService } from "@/client"
import { AuthLayout } from "@/components/Common/AuthLayout"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { LoadingButton } from "@/components/ui/loading-button"
import { PasswordInput } from "@/components/ui/password-input"
import useAuth, { isLoggedIn } from "@/hooks/useAuth"
import { truncateAddress } from "@/lib/wallet-utils"

const formSchema = z.object({
  passphrase: z.string().min(1, { message: "Passphrase is required" }),
})

type FormData = z.infer<typeof formSchema>

export const Route = createFileRoute("/login")({
  component: Login,
  beforeLoad: async () => {
    if (isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Log In" }],
  }),
})

function Login() {
  const { loginMutation } = useAuth()
  const [selectedWallet, setSelectedWallet] = useState<WalletInfo | null>(null)

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

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      passphrase: "",
    },
  })

  const onSubmit = (data: FormData) => {
    if (loginMutation.isPending) return

    // Determine which wallet address to use as username
    let username: string
    if (multiWallet) {
      if (!selectedWallet) return
      username = selectedWallet.address
    } else if (wallets.length === 1) {
      username = wallets[0].address
    } else {
      // No wallets configured — server will return 503; setup flow should handle this
      username = "node"
    }

    loginMutation.mutate(
      { username, password: data.passphrase },
      {
        onError: (err) => {
          const isAuthError = err instanceof ApiError && err.status === 401
          form.setError("passphrase", {
            message: isAuthError
              ? "Invalid passphrase"
              : "Service unavailable, please try again",
          })
          // Only send user back to wallet picker on auth failure, not network errors
          if (multiWallet && isAuthError) {
            setSelectedWallet(null)
            form.reset()
          }
        },
      },
    )
  }

  // Wallet list failed to load — can't determine auth mode
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

  // Multi-wallet: wallet selection step
  if (multiWallet && selectedWallet === null) {
    return (
      <AuthLayout>
        <div className="flex flex-col gap-6">
          <div className="flex flex-col items-center gap-2 text-center">
            <h1 className="text-2xl font-bold">Choose a wallet</h1>
            <p className="text-sm text-muted-foreground">
              Select the wallet you want to connect with.
            </p>
          </div>
          <div className="flex flex-col gap-2">
            {wallets.map((wallet) => (
              <button
                key={wallet.address}
                type="button"
                onClick={() => setSelectedWallet(wallet)}
                className="flex items-center gap-3 rounded-lg border p-4 text-left transition-colors hover:bg-accent hover:text-accent-foreground"
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
        </div>
      </AuthLayout>
    )
  }

  // Single-wallet or after wallet selection: passphrase step
  return (
    <AuthLayout>
      <Form {...form}>
        <form
          onSubmit={form.handleSubmit(onSubmit)}
          className="flex flex-col gap-6"
        >
          <div className="flex flex-col items-center gap-2 text-center">
            {multiWallet && selectedWallet ? (
              <>
                <h1 className="text-2xl font-bold">
                  {selectedWallet.name ||
                    truncateAddress(selectedWallet.address)}
                </h1>
                <p className="text-sm text-muted-foreground">
                  Enter the passphrase for this wallet.
                </p>
                <button
                  type="button"
                  onClick={() => {
                    setSelectedWallet(null)
                    form.reset()
                  }}
                  className="text-xs text-muted-foreground underline underline-offset-2"
                >
                  ← Choose a different wallet
                </button>
              </>
            ) : (
              <>
                <h1 className="text-2xl font-bold">Unlock your node</h1>
                <p className="text-sm text-muted-foreground">
                  Enter your passphrase to continue.
                </p>
              </>
            )}
          </div>

          <div className="grid gap-4">
            <FormField
              control={form.control}
              name="passphrase"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Passphrase</FormLabel>
                  <FormControl>
                    <PasswordInput
                      data-testid="passphrase-input"
                      placeholder="Your passphrase"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage className="text-xs" />
                </FormItem>
              )}
            />

            <LoadingButton type="submit" loading={loginMutation.isPending}>
              Unlock
            </LoadingButton>
          </div>
        </form>
      </Form>
    </AuthLayout>
  )
}
