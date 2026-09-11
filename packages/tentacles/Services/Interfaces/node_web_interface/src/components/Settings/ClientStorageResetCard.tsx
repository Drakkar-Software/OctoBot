import { KeyRound } from "lucide-react"
import { resetClientStorage } from "@/lib/client-storage-reset"
import { RESET_CONFIRM_MESSAGE } from "@/lib/ui-recovery-constants"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Button } from "@/components/ui/button"

export function ClientStorageResetCard() {
  const handleResetClick = () => {
    if (!window.confirm(RESET_CONFIRM_MESSAGE)) {
      return
    }
    void resetClientStorage("manual_settings")
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <KeyRound className="size-5" />
          Local browser data
        </CardTitle>
        <CardDescription>
          Clear all local data for this app on this device, including sign-in,
          wallet encryption keys, templates, and UI cache. You will need to sign
          in again. Use this if the app behaves incorrectly and recovery from
          the error screen did not help.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Button type="button" variant="destructive" onClick={handleResetClick}>
          Reset local browser data
        </Button>
      </CardContent>
    </Card>
  )
}
