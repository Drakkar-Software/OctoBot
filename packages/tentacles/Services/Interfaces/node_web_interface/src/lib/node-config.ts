import { loadPassword } from "@/lib/device-key"

export async function buildAuthHeader() {
  const username = localStorage.getItem("auth_username") || "node"
  const password = (await loadPassword()) ?? ""
  return `Basic ${btoa(`${username}:${password}`)}`
}

export async function fetchNodeConfig() {
  const res = await fetch("/api/v1/nodes/config", {
    headers: { Authorization: await buildAuthHeader() },
  })
  return res.json()
}
