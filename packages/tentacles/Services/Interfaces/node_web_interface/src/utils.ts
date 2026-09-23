import type { ApiError } from "@/lib/api-error"
import { getApiErrorResponseBody, isApiError } from "@/lib/api-error"

export function extractErrorMessage(err: ApiError): string {
  if (isApiError(err)) {
    const body = getApiErrorResponseBody(err)
    const errDetail = (body as { detail?: unknown })?.detail
    if (Array.isArray(errDetail) && errDetail.length > 0) {
      const first = errDetail[0] as { msg?: string }
      return first.msg ?? err.message
    }
    if (errDetail && typeof errDetail === "object") {
      const message = (errDetail as { message?: unknown }).message
      if (typeof message === "string" && message.length > 0) {
        return message
      }
    }
    if (typeof errDetail === "string") {
      return errDetail
    }
    return err.message
  }

  return "Something went wrong."
}

export const handleError = function (
  this: (msg: string) => void,
  err: ApiError,
) {
  const errorMessage = extractErrorMessage(err)
  this(errorMessage)
}

export const getInitials = (name: string): string => {
  return name
    .split(" ")
    .slice(0, 2)
    .map((word) => word[0])
    .join("")
    .toUpperCase()
}
