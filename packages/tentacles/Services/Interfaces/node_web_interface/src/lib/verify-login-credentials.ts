import type { User } from "@/client"
import { LoginService } from "@/client"
import { buildBasicAuthorizationHeader } from "@/lib/basic-auth"

/** Verify wallet + passphrase without writing `auth_username` (avoids session probe races). */
export async function verifyLoginCredentials(
  username: string,
  password: string,
): Promise<User> {
  const response = await LoginService.loginTestAuth({
    headers: {
      Authorization: buildBasicAuthorizationHeader(username, password),
    },
    throwOnError: true,
  })
  return response.data
}
