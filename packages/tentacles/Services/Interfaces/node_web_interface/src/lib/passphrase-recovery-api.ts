import { ApiError } from "@/client"

export type RecoverWalletFromSeedRequest = {
  address: string
  new_passphrase: string
  seed?: string | null
  private_key?: string | null
}

export async function recoverWalletFromSeed(
  body: RecoverWalletFromSeedRequest,
): Promise<void> {
  const response = await fetch("/api/v1/setup/wallet/recover-from-seed", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    let message = response.statusText
    try {
      const payload = (await response.json()) as { detail?: string }
      if (payload.detail) {
        message = payload.detail
      }
    } catch {
      // ignore JSON parse errors
    }
    throw new ApiError(
      {
        url: "/api/v1/setup/wallet/recover-from-seed",
        method: "POST",
        headers: {},
      },
      {
        url: response.url,
        ok: response.ok,
        status: response.status,
        statusText: response.statusText,
        body: message,
      },
      message,
    )
  }
}
