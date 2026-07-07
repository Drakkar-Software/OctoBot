import { Link } from "@tanstack/react-router"
import { Star, Upload } from "lucide-react"
import { useState } from "react"

import { CreateGenericProcessBotDialog } from "@/components/Common/CreateGenericProcessBotDialog"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { getAssetPath } from "@/lib/utils"

export function NewBotCards() {
  const [genericProcessDialogOpen, setGenericProcessDialogOpen] = useState(false)
  const launchImage = getAssetPath("images/octobot_launching_512.png")
  const designImage = getAssetPath("images/octobot_design_512.png")
  const labImage = getAssetPath("images/octobot_lab_512.png")

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Card className="cursor-not-allowed bg-muted/50 opacity-50">
        <CardHeader className="flex-1">
          <div className="flex justify-center">
            <img
              src={launchImage}
              alt="Launching OctoBot"
              className="size-36 object-contain"
            />
          </div>
          <CardTitle className="flex items-center gap-2">
            Pre-configured setup
          </CardTitle>
          <CardDescription>
            Start fast with curated presets. Available soon on octobot.cloud and
            from the mobile app.
          </CardDescription>
        </CardHeader>
        <CardContent className="mt-auto flex items-center justify-between pt-2">
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="inline-flex items-center gap-1 text-warn">
                <Star className="size-5 fill-warn" />
              </span>
            </TooltipTrigger>
            <TooltipContent>Easy to setup</TooltipContent>
          </Tooltip>
          <Button disabled>Browse presets</Button>
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
            Build with your own rules. Available soon on octobot.cloud and from
            the mobile app.
          </CardDescription>
        </CardHeader>
        <CardContent className="mt-auto flex items-center justify-between pt-2">
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="inline-flex items-center gap-1 text-warn">
                <Star className="size-5 fill-warn" />
                <Star className="size-5 fill-warn" />
              </span>
            </TooltipTrigger>
            <TooltipContent>Easy to medium setup</TooltipContent>
          </Tooltip>
          <Button variant="outline" disabled>
            <Link to="/octobots/new/builder">Build my OctoBot</Link>
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
            Start an OctoBot you configure manually with its dedicated
            interface. Best for backtesting and in-depth analysis — aimed at
            strategy creators who want full control.
          </CardDescription>
        </CardHeader>
        <CardContent className="mt-auto flex items-center justify-between pt-2">
          <Tooltip>
            <TooltipTrigger asChild>
              <span className="inline-flex items-center gap-1 text-warn">
                <Star className="size-5 fill-warn" />
                <Star className="size-5 fill-warn" />
                <Star className="size-5 fill-warn" />
              </span>
            </TooltipTrigger>
            <TooltipContent>Advanced setup</TooltipContent>
          </Tooltip>
          <Button
            variant="outline"
            onClick={() => setGenericProcessDialogOpen(true)}
          >
            Start manual OctoBot
          </Button>
        </CardContent>
      </Card>
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
      </div>
    </div>
  )
}
