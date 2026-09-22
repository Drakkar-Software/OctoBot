import type { InternalAxiosRequestConfig } from "axios"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { client } from "@/client/client.gen"

vi.mock("@/lib/device-key", () => ({
  loadPassword: vi.fn(),
}))

vi.mock("@/hooks/useAuth", () => ({
  clearAuth: vi.fn(() => Promise.resolve()),
}))

vi.mock("@/lib/open-api-401-login-redirect", () => ({
  shouldRedirectToLoginOn401: vi.fn(() => true),
}))

import { loadPassword } from "@/lib/device-key"
import { clearAuth } from "@/hooks/useAuth"
import { shouldRedirectToLoginOn401 } from "@/lib/open-api-401-login-redirect"
import {
  configureApiClient,
  resetApiClientConfigurationForTests,
} from "@/lib/configure-api-client"

function getRequestInterceptor() {
  const manager = client.instance.interceptors.request as unknown as {
    handlers: Array<{ fulfilled: (config: InternalAxiosRequestConfig) => unknown }>
  }
  const handler = manager.handlers[manager.handlers.length - 1]
  if (!handler?.fulfilled) {
    throw new Error("request interceptor not registered")
  }
  return handler.fulfilled
}

function getResponseInterceptor() {
  const manager = client.instance.interceptors.response as unknown as {
    handlers: Array<{ fulfilled: (response: { status: number }) => unknown }>
  }
  const handler = manager.handlers[manager.handlers.length - 1]
  if (!handler?.fulfilled) {
    throw new Error("response interceptor not registered")
  }
  return handler.fulfilled
}

const localStorageStore: Record<string, string> = {}

describe("configureApiClient", () => {
  beforeEach(() => {
    resetApiClientConfigurationForTests()
    Object.keys(localStorageStore).forEach((key) => {
      delete localStorageStore[key]
    })
    vi.stubGlobal("localStorage", {
      getItem: (key: string) => localStorageStore[key] ?? null,
      setItem: (key: string, value: string) => {
        localStorageStore[key] = value
      },
      removeItem: (key: string) => {
        delete localStorageStore[key]
      },
      clear: () => {
        Object.keys(localStorageStore).forEach((key) => {
          delete localStorageStore[key]
        })
      },
    })
    vi.mocked(loadPassword).mockReset()
    vi.mocked(clearAuth).mockClear()
    vi.mocked(shouldRedirectToLoginOn401).mockReturnValue(true)
    vi.stubGlobal("sessionStorage", {
      getItem: () => null,
      setItem: vi.fn(),
      removeItem: vi.fn(),
      clear: vi.fn(),
    })
    vi.stubGlobal("window", {
      location: { pathname: "/app/octobots", href: "" },
    })
  })

  it("request interceptor adds Basic Authorization when credentials exist", async () => {
    localStorage.setItem("auth_username", "0xwallet")
    vi.mocked(loadPassword).mockResolvedValue("passphrase")
    configureApiClient()

    const axios = await import("axios")
    const runRequest = getRequestInterceptor()
    const config = {
      headers: new axios.AxiosHeaders(),
    } as InternalAxiosRequestConfig

    const updated = (await runRequest(config)) as InternalAxiosRequestConfig
    expect(String(updated.headers.get("Authorization"))).toMatch(/^Basic /)
  })

  it("response interceptor redirects on 401 when policy allows", async () => {
    configureApiClient()
    const runResponse = getResponseInterceptor()
    await runResponse({ status: 401 })
    expect(clearAuth).toHaveBeenCalled()
    expect(window.location.href).toBe("/app/login")
  })
})
