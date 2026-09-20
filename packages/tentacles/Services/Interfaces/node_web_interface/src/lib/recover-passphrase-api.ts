export type RecoverPassphraseRequest = {
  new_passphrase: string
  address?: string | null
  seed?: string | null
  private_key?: string | null
}

export type RecoverPassphraseResponse = {
  address: string
}

export class RecoverPassphraseApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export async function recoverWalletPassphrase(
  body: RecoverPassphraseRequest,
): Promise<RecoverPassphraseResponse> {
  const response = await fetch("/api/v1/setup/wallet/recover-passphrase", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    let detail = await response.text()
    try {
      const parsed = JSON.parse(detail) as { detail?: string }
      if (parsed.detail) {
        detail = parsed.detail
      }
    } catch {
      // keep raw body
    }
    throw new RecoverPassphraseApiError(
      response.status,
      detail || "Recovery failed",
    )
  }
  return response.json()
}
