import { ApiError } from "@/client"
import { extractErrorMessage } from "@/utils"

const RECOVER_SEED_MISMATCH =
  "That seed phrase or private key does not match this wallet."

const RECOVER_SEED_UNVERIFIED =
  "That seed phrase or private key could not be verified. Check spelling, word order, and that you entered the phrase for this wallet."

const RECOVER_WALLET_NOT_ON_NODE = "This wallet is not set up on this node."

const RECOVER_RATE_LIMIT =
  "Too many attempts. Wait a few minutes, then try again."

const RECOVER_UNAVAILABLE_DEFAULT =
  "Passphrase recovery is not available on this node."

const GENERIC_SUBMIT_ERROR = "Something went wrong."

export type RecoverSeedSubmitErrorResult = {
  message: string
  unavailable: boolean
}

function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError
}

export function resolveRecoverSeedSubmitError(
  error: unknown,
): RecoverSeedSubmitErrorResult {
  if (!isApiError(error)) {
    return { message: GENERIC_SUBMIT_ERROR, unavailable: false }
  }

  if (error.status === 503) {
    const detail = extractErrorMessage(error)
    return {
      message:
        detail !== GENERIC_SUBMIT_ERROR ? detail : RECOVER_UNAVAILABLE_DEFAULT,
      unavailable: true,
    }
  }

  if (error.status === 429) {
    return { message: RECOVER_RATE_LIMIT, unavailable: false }
  }

  if (error.status === 401) {
    return { message: RECOVER_SEED_MISMATCH, unavailable: false }
  }

  if (error.status === 422) {
    return { message: RECOVER_SEED_UNVERIFIED, unavailable: false }
  }

  if (error.status === 404) {
    return { message: RECOVER_WALLET_NOT_ON_NODE, unavailable: false }
  }

  return {
    message: extractErrorMessage(error),
    unavailable: false,
  }
}
