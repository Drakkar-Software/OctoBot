import { Link } from "@tanstack/react-router"
import { Upload } from "lucide-react"
import { useState } from "react"

import { CreateGenericProcessBotDialog } from "@/components/Common/CreateGenericProcessBotDialog"
import { StartAutomationDialog } from "@/components/Setup/StartAutomationDialog"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { getAssetPath } from "@/lib/utils"

type NewBotCardsProps = {
  onFinishSetup?: () => void
  onSkip?: () => void
}

function ComplexityBadge({ label }: { label: string }) {
  return (
    <span className="rounded-full border px-2 py-0.5 text-xs text-muted-foreground">
      {label}
    </span>
  )
}

export function NewBotCards({ onFinishSetup, onSkip }: NewBotCardsProps) {
  const [genericProcessDialogOpen, setGenericProcessDialogOpen] = useState(false)
  const [automationDialogOpen, setAutomationDialogOpen] = useState(false)
  const launchImage = getAssetPath("images/octobot_launching_512.png")
  const designImage = getAssetPath("images/octobot_design_512.png")
  const labImage = getAssetPath("images/octobot_lab_512.png")

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Card>
        <CardHeader className="flex-1">
          <div className="flex justify-center">
            <img
              src={launchImage}
              alt="Launching OctoBot"
              className="size-36 object-contain"
            />
          </div>
          <CardTitle className="flex items-center gap-2">
            Pre-configured automation
          </CardTitle>
          <CardDescription>
            Start configurable strategies from the OctoBot interface. Includes
            Baskets, DCA, grid trading and more.
          </CardDescription>
        </CardHeader>
        <CardContent className="mt-auto flex items-center justify-between pt-2">
          <ComplexityBadge label="Everyone" />
          <Button type="button" onClick={() => setAutomationDialogOpen(true)}>
            Start OctoBot
          </Button>
        </CardContent>
      </Card>
      <Card className="cursor-not-allowed bg-muted/50 opacity-50">
        <CardHeader className="flex-1">
          <div className="flex justify-center">
            <img
              src={designImage}
              alt="Design strategy"
              className="size-36 object-contain"
            />
          </div>
          <CardTitle className="flex items-center gap-2">
            Your own rules
          </CardTitle>
          <CardDescription>
            Build with your own rules, with your own logic, indicators and
            conditions. Coming soon.
          </CardDescription>
        </CardHeader>
        <CardContent className="mt-auto flex items-center justify-between pt-2">
          <ComplexityBadge label="Advanced" />
          <Button variant="outline" disabled>
            Available soon
          </Button>
        </CardContent>
      </Card>
      <Card>
        <CardHeader className="flex-1">
          <div className="flex justify-center">
            <img
              src={labImage}
              alt="Custom configuration"
              className="size-32 object-contain"
            />
          </div>
          <CardTitle className="flex items-center gap-2">
            Manual configuration
          </CardTitle>
          <CardDescription>
            Configure an OctoBot manually with its dedicated interface for
            backtesting and advanced control.
          </CardDescription>
        </CardHeader>
        <CardContent className="mt-auto flex items-center justify-between pt-2">
          <ComplexityBadge label="Expert" />
          <Button
            variant="outline"
            onClick={() => setGenericProcessDialogOpen(true)}
          >
            Start manual OctoBot
          </Button>
        </CardContent>
      </Card>
      <StartAutomationDialog
        open={automationDialogOpen}
        onOpenChange={setAutomationDialogOpen}
        onAcknowledge={onFinishSetup ?? onSkip}
      />
      <CreateGenericProcessBotDialog
        open={genericProcessDialogOpen}
        onOpenChange={setGenericProcessDialogOpen}
      />
      <div className="col-span-full flex flex-col items-center gap-1 text-sm text-muted-foreground">
        <span>Already have a saved configuration?</span>
        <Link
          to="/octobots/import"
          className="inline-flex items-center gap-1 underline underline-offset-4 hover:text-foreground"
        >
          <Upload className="size-3.5" />
          Restore from a file
        </Link>
        {onSkip && (
          <button
            type="button"
            onClick={onSkip}
            className="mt-2 text-sm text-muted-foreground underline underline-offset-4 hover:text-foreground"
          >
            Skip this step
          </button>
        )}
      </div>
    </div>
  )
}
