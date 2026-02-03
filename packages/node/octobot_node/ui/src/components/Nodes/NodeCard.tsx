import { useQuery } from "@tanstack/react-query"
import { Activity, Server, Users } from "lucide-react"
import type { Node } from "@/client"

import { NodesService } from "@/client"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

function getNodeQueryOptions() {
  return {
    queryFn: () => NodesService.getCurrentNode(),
    queryKey: ["node"],
    refetchInterval: 5000, // Refetch every 5 seconds
  }
}

function getNodesQueryOptions() {
  return {
    queryFn: () => NodesService.getCurrentNode(),
    queryKey: ["nodes"],
    refetchInterval: 5000, // Refetch every 5 seconds
  }
}

interface NodeCardProps {
  node: Node
  compact?: boolean
}

export function NodeCardSmall({ node, compact = true }: NodeCardProps) {
  const statusColor =
    node.status === "running" ? "bg-green-500" : "bg-gray-500"

  return (
    <Card className={compact ? "h-full" : ""}>
      <CardHeader className={compact ? "pb-3" : ""}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Server className="h-4 w-4 text-muted-foreground" />
            <CardTitle className="text-base">Node</CardTitle>
          </div>
          <div className="flex items-center gap-2">
            <div className={`h-2 w-2 rounded-full ${statusColor}`} />
            <Badge variant={node.status === "running" ? "default" : "secondary"} className="text-xs">
              {node.status}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className={compact ? "pt-0 space-y-2" : "space-y-4"}>
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-1.5">
            <Activity className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-muted-foreground">Type</span>
          </div>
          <Badge variant="outline" className="capitalize text-xs">
            {node.node_type}
          </Badge>
        </div>

        {node.workers !== null && (
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-1.5">
              <Users className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="text-muted-foreground">Workers</span>
            </div>
            <span className="text-sm font-medium">{node.workers}</span>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function NodeCardContent() {
  const { data: node, isLoading } = useQuery(getNodeQueryOptions())

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-32" />
          <Skeleton className="h-4 w-48 mt-2" />
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-4">
            <Skeleton className="h-20 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!node) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Node Information</CardTitle>
          <CardDescription>Unable to load node information</CardDescription>
        </CardHeader>
      </Card>
    )
  }

  const statusColor =
    node.status === "running" ? "bg-green-500" : "bg-gray-500"

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Server className="h-5 w-5" />
              Node Status
            </CardTitle>
            <CardDescription>Current node configuration and status</CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <div className={`h-3 w-3 rounded-full ${statusColor}`} />
            <Badge variant={node.status === "running" ? "default" : "secondary"}>
              {node.status}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between p-3 border rounded-lg">
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">Node Type</span>
            </div>
            <Badge variant="outline" className="capitalize">
              {node.node_type}
            </Badge>
          </div>


          {node.workers !== null && (
            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div className="flex items-center gap-2">
                <Users className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">Workers</span>
              </div>
              <span className="text-sm font-medium">{node.workers}</span>
            </div>
          )}

          {node.redis_url && (
            <div className="flex flex-col gap-1 p-3 border rounded-lg">
              <span className="text-sm font-medium">Redis URL</span>
              <span className="text-xs text-muted-foreground font-mono truncate">
                {node.redis_url}
              </span>
            </div>
          )}

          {node.sqlite_file && (
            <div className="flex flex-col gap-1 p-3 border rounded-lg">
              <span className="text-sm font-medium">SQLite File</span>
              <span className="text-xs text-muted-foreground font-mono">
                {node.sqlite_file}
              </span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

export default function NodeCard() {
  return <NodeCardContent />
}

export { getNodesQueryOptions }

