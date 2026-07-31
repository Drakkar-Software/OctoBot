import { loadPassword } from "@/lib/device-key"

export async function buildAuthHeader() {
  const username = localStorage.getItem("auth_username")
  const password = await loadPassword()
  if (!username || !password) {
    throw new Error("No active wallet session")
  }
  return `Basic ${btoa(`${username}:${password}`)}`
}

export async function fetchNodeConfig() {
  const res = await fetch("/api/v1/nodes/config", {
    headers: { Authorization: await buildAuthHeader() },
  })
  return res.json()
}
