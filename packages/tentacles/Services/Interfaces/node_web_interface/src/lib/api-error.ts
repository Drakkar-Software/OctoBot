import axios, { type AxiosError } from "axios"

export type ApiError = AxiosError

export function isApiError(error: unknown): error is ApiError {
  return axios.isAxiosError(error)
}

export function getApiErrorStatus(error: ApiError): number | undefined {
  return error.response?.status
}

/** Build an Axios-shaped error for unit tests (replaces legacy `ApiError` class). */
export function createTestApiError(
  status: number,
  body: unknown,
  message = "Request failed",
): ApiError {
  return {
    isAxiosError: true,
    message,
    name: "AxiosError",
    response: {
      status,
      data: body,
      statusText: "",
      headers: {},
      config: {} as ApiError["config"],
    },
    config: {} as ApiError["config"],
    toJSON: () => ({}),
  } as ApiError
}

export function formatApiErrorDetailMessage(
  error: unknown,
  fallback: string,
): string {
  if (isApiError(error)) {
    const body = getApiErrorResponseBody(error)
    const detail = (body as { detail?: unknown } | undefined)?.detail
    if (typeof detail === "string" && detail.trim().length > 0) {
      return detail
    }
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0] as { msg?: string }
      if (typeof first?.msg === "string" && first.msg.trim().length > 0) {
        return first.msg
      }
    }
    if (error.message.trim().length > 0) {
      return error.message
    }
  }
  if (error instanceof Error && error.message.trim().length > 0) {
    return error.message
  }
  return fallback
}

export function getApiErrorResponseBody(error: ApiError): unknown {
  return error.response?.data
}
