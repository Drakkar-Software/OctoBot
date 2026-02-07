import { FileText } from "lucide-react"

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

export function Logs() {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <FileText className="h-5 w-5" />
          <CardTitle>Logs</CardTitle>
        </div>
        <CardDescription>System and application logs</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col gap-2">
          <div className="rounded-lg border bg-muted/50 p-4 font-mono text-sm">
            <div className="text-muted-foreground">
              Logs functionality will be available soon.
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

