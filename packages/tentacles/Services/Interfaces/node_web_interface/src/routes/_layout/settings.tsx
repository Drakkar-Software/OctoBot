import { createFileRoute } from "@tanstack/react-router"
import { Shield, Sliders } from "lucide-react"

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

export const Route = createFileRoute("/_layout/settings")({
  component: Settings,
  head: () => ({
    meta: [{ title: "Settings" }],
  }),
})

function Settings() {
  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">
          Tune security, node behavior, and integrations.
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Shield className="size-4" />
              Security
            </CardTitle>
            <CardDescription>
              Manage admin credentials and access rules.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Configure admin username/password and authentication preferences.
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sliders className="size-4" />
              Node configuration
            </CardTitle>
            <CardDescription>
              Scheduler, storage, and worker settings.
            </CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Adjust Redis URI, SQLite file path, and worker count.
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
