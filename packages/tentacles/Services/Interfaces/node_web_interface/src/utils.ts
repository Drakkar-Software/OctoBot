import { AxiosError } from "axios"
import type { ApiError } from "./client"

export function extractErrorMessage(err: ApiError): string {
  if (err instanceof AxiosError) {
    return err.message
  }

  const errDetail = (err.body as { detail?: unknown })?.detail
  if (Array.isArray(errDetail) && errDetail.length > 0) {
    const first = errDetail[0] as { msg?: string }
    return first.msg ?? "Something went wrong."
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
  if (typeof err.body === "string" && err.body.trim().length > 0) {
    return err.body
  }
  if (
    typeof err.message === "string" &&
    err.message.trim().length > 0 &&
    err.message !== err.statusText
  ) {
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
