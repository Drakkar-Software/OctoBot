import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/_layout/octobots/new/builder')({
  component: RouteComponent,
})

function RouteComponent() {
  return <div></div>
}
