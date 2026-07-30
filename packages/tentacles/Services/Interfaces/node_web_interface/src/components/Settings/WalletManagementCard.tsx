import { useQuery, useQueryClient } from "@tanstack/react-query"
import { LogOut, Wallet } from "lucide-react"
import { WalletsService } from "@/client"
import { CardCornerButton } from "@/components/Settings/CardCornerButton"
import { AddWalletDialog } from "@/components/Settings/WalletManagement/AddWalletDialog"
import { WalletRow } from "@/components/Settings/WalletManagement/WalletRow"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import useAuth from "@/hooks/useAuth"

export function WalletManagementCard() {
  const queryClient = useQueryClient()
  const { user, logout } = useAuth()
  const { data: wallets = [], isLoading } = useQuery({
    queryKey: ["wallets"],
    queryFn: () => WalletsService.listWallets(),
  })

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ["wallets"] })
  }

  const currentAddress = localStorage.getItem("auth_username") ?? ""
  const currentAddressLower = currentAddress.toLowerCase()
  const displayedWallets = user?.is_superuser
    ? wallets
    : wallets.filter((w) => w.address.toLowerCase() === currentAddressLower)

  return (
    <Card className="relative">
      <CardCornerButton
        icon={LogOut}
        label="Log out"
        onClick={() => void logout()}
      />
      <CardHeader className="pr-12">
        <CardTitle className="flex items-center gap-2">
          <Wallet className="size-4" />
          Wallet management
        </CardTitle>
        <CardDescription>
          Manage wallets that can log in to this node. Each wallet has its own
          passphrase and task visibility.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading wallets…</p>
        ) : (
          <>
            <div className="grid gap-2 sm:grid-cols-2">
              {displayedWallets.map((wallet) => (
                <WalletRow
                  key={wallet.address}
                  wallet={wallet}
                  onRefresh={refresh}
                  showRemove={user?.is_superuser === true}
                  showExport={user?.is_superuser === true || wallet.address.toLowerCase() === currentAddressLower}
                  currentUserAddress={currentAddress}
                />
              ))}
            </div>
            {user?.is_superuser && <AddWalletDialog onSuccess={refresh} />}
          </>
        )}
      </CardContent>
    </Card>
  )
}
