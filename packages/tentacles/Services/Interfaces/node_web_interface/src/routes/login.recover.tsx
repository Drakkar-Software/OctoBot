import { createFileRoute, redirect } from "@tanstack/react-router"

import { PassphraseRecoveryScreen } from "@/components/Auth/PassphraseRecoveryScreen"
import { isLoggedIn } from "@/hooks/useAuth"

export const Route = createFileRoute("/login/recover")({
  component: PassphraseRecoveryScreen,
  beforeLoad: async () => {
    if (isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Recover passphrase" }],
  }),
})
