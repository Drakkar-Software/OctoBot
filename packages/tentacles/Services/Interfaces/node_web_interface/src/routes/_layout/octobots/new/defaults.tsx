import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/_layout/octobots/new/defaults')({
  component: RouteComponent,
})

function RouteComponent() {
  return <div></div>
}
