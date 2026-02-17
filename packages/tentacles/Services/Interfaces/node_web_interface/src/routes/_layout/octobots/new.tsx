import { createFileRoute, Link } from "@tanstack/react-router"
import { Bot, Layers, Star, StarHalf, StarOff, Wrench } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { getAssetPath } from "@/lib/utils"

export const Route = createFileRoute("/_layout/octobots/new")({
  component: NewOctobot,
  head: () => ({
    meta: [{ title: "New OctoBot" }],
  }),
})

function NewOctobot() {
  const launchImage = getAssetPath("images/octobot_launching_512.png")
  const designImage = getAssetPath("images/octobot_design_512.png")
  const labImage = getAssetPath("images/octobot_lab_512.png")

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Create a new OctoBot</h1>
        <p className="text-md text-muted-foreground">
          Choose how to start your OctoBot. You can select a pre-configured setup, design your own strategy, or start with a custom configuration for full control. Each option is tailored to different levels of experience and customization needs.
        </p>
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="border-primary/40 bg-primary/5">
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
              Start fast with curated presets. Ideal
              for quick launches with minimal setup.
            </CardDescription>
          </CardHeader>
          <CardContent className="mt-auto flex items-center justify-between pt-2">
            <Tooltip>
              <TooltipTrigger asChild>
                <span className="inline-flex items-center gap-1 text-amber-400">
                  <Star className="size-5 fill-amber-400" />
                </span>
              </TooltipTrigger>
              <TooltipContent>Easy to setup</TooltipContent>
            </Tooltip>
            <Button asChild>
              <Link to="/octobots/new/presets">Browse presets</Link>
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
              Build with your own rules.
              Available soon on octobot.cloud and from the mobile app.
            </CardDescription>
          </CardHeader>
          <CardContent className="mt-auto flex items-center justify-between pt-2">
            <Tooltip>
              <TooltipTrigger asChild>
                <span className="inline-flex items-center gap-1 text-amber-400">
                  <Star className="size-5 fill-amber-400" />
                  <Star className="size-5 fill-amber-400" />
                </span>
              </TooltipTrigger>
              <TooltipContent>Easy to medium setup</TooltipContent>
            </Tooltip>
            <Button variant="outline" disabled>
              <Link to="/octobots/new/builder">
                Build my OctoBot
              </Link>
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
              Custom configuration
            </CardTitle>
            <CardDescription>
              Full control with advanced options. You’ll configure everything
              after start, including each parameter.
            </CardDescription>
          </CardHeader>
          <CardContent className="mt-auto flex items-center justify-between pt-2">
            <Tooltip>
              <TooltipTrigger asChild>
                <span className="inline-flex items-center gap-1 text-amber-400">
                  <Star className="size-5 fill-amber-400" />
                  <Star className="size-5 fill-amber-400" />
                  <Star className="size-5 fill-amber-400" />
                </span>
              </TooltipTrigger>
              <TooltipContent>Advanced setup</TooltipContent>
            </Tooltip>
            <Button variant="outline">
              <Link to="/octobots/new/defaults">Start with defaults</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
