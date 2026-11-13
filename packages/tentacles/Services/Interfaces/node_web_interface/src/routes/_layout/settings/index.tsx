import { createFileRoute } from "@tanstack/react-router"

import { MobileUiCard } from "@/components/Setup/MobileUiCard"
import { ClientEncryptionKeysCard } from "@/components/Settings/ClientEncryptionKeysCard"
import { NodeConfigurationCard } from "@/components/Settings/NodeConfigurationCard"
import { WalletManagementCard } from "@/components/Settings/WalletManagementCard"
import { SupportCard } from "@/components/Support/SupportCard"

export const Route = createFileRoute("/_layout/settings/")({
  component: Settings,
  head: () => ({
    meta: [{ title: "Settings" }],
  }),
})

function Settings() {
  return (
    <div className="flex flex-col gap-8">
      <div className="grid gap-4 md:grid-cols-2">
        <NodeConfigurationCard />
        <MobileUiCard />
        <SupportCard />
        <WalletManagementCard />
        <ClientEncryptionKeysCard />
      </div>
    </div>
  )
}
