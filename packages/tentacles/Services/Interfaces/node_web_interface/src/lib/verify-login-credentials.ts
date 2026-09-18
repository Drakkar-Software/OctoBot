import { ApiError } from "@/client"
import { OpenAPI } from "@/client/core/OpenAPI"
import type { User } from "@/client"
import { buildBasicAuthorizationHeader } from "@/lib/basic-auth"

/** Verify wallet + passphrase without writing `auth_username` (avoids session probe races). */
export async function verifyLoginCredentials(
  username: string,
  password: string,
): Promise<User> {
  const base = (OpenAPI.BASE ?? "").replace(/\/$/, "")
  const url = `${base}/api/v1/login/test`
  const response = await fetch(url, {
    headers: { Authorization: buildBasicAuthorizationHeader(username, password) },
  })
  let body: unknown = null
  try {
    body = await response.json()
  } catch {
    body = null
  }
  if (!response.ok) {
    throw new ApiError(
      { method: "GET", url },
      {
        url,
        ok: false,
        status: response.status,
        statusText: response.statusText,
        body,
      },
      response.statusText,
    )
  }
  return body as User
}
