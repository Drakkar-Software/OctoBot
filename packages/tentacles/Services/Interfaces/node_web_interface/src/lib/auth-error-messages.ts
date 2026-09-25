/**
 * Passphrases are verified exactly as entered on the server; leading and trailing
 * whitespace are not removed.
 */

import { ApiError } from "@/client"
import {
  API_AUTH_ERROR_CODES,
  type ApiAuthErrorCode,
  type AuthErrorCode,
  CLIENT_AUTH_ERROR_CODES,
} from "@/lib/auth-error-codes"
import { parseAuthErrorCodeFromApiError } from "@/lib/parse-auth-api-error"
import { passphraseHasEdgeWhitespace } from "@/lib/passphrase-edge"

export type AuthErrorPresentation = {
  title: string
  explanation: string
  guidance: string[]
}

export type LoginAuthContext = {
  multiWallet: boolean
}

const LOGIN_RATE_LIMIT_PRESENTATION: AuthErrorPresentation = {
  title: "Too many login attempts",
  explanation: "Try again later.",
  guidance: [],
}

const API_AUTH_MESSAGES: Record<ApiAuthErrorCode, AuthErrorPresentation> = {
  [API_AUTH_ERROR_CODES.AUTH_PASSPHRASE_REQUIRED]: {
    title: "Enter your passphrase",
    explanation: "",
    guidance: [],
  },
  [API_AUTH_ERROR_CODES.AUTH_WALLET_ADDRESS_REQUIRED]: {
    title: "Choose a wallet",
    explanation: "Select your wallet, then enter your passphrase.",
    guidance: [],
  },
  [API_AUTH_ERROR_CODES.AUTH_WALLET_NOT_FOUND]: {
    title: "Wallet not found here",
    explanation: "This wallet is not set up on the node you are using.",
    guidance: [],
  },
  [API_AUTH_ERROR_CODES.AUTH_INVALID_PASSPHRASE]: {
    title: "Wrong passphrase",
    explanation: "Try again.",
    guidance: [],
  },
  [API_AUTH_ERROR_CODES.AUTH_NODE_NOT_CONFIGURED]: {
    title: "Setup needed",
    explanation: "Finish setting up this node before you sign in.",
    guidance: [],
  },
}

const INVALID_PASSPHRASE_EXPLANATION_WITH_EDGE_WHITESPACE =
  "Check for spaces at the start or end of what you entered."

const LOGIN_EDGE_WHITESPACE_TIP = "Remove those spaces and try again."

const CLIENT_AUTH_MESSAGES: Record<
  (typeof CLIENT_AUTH_ERROR_CODES)[keyof typeof CLIENT_AUTH_ERROR_CODES],
  AuthErrorPresentation
> = {
  [CLIENT_AUTH_ERROR_CODES.AUTH_SESSION_INCOMPLETE]: {
    title: "Sign-in problem on this browser",
    explanation:
      "Your wallet is remembered here, but your passphrase could not be read.",
    guidance: [
      'On the recovery screen, use "Reset local browser data", then sign in again.',
      "Allow site data and storage for this site in your browser settings.",
    ],
  },
  [CLIENT_AUTH_ERROR_CODES.DEVICE_STORAGE_BLOCKED]: {
    title: "Can't save sign-in",
    explanation: "Your browser blocked saved sign-in for this site.",
    guidance: [],
  },
  [CLIENT_AUTH_ERROR_CODES.NETWORK_ERROR]: {
    title: "Can't connect",
    explanation: "This page could not reach your OctoBot node.",
    guidance: [],
  },
  [CLIENT_AUTH_ERROR_CODES.SESSION_CLEARED]: {
    title: "Session expired",
    explanation: "Please sign in again with your passphrase.",
    guidance: [],
  },
}

export function getAuthErrorPresentation(
  code: AuthErrorCode,
): AuthErrorPresentation {
  return code in API_AUTH_MESSAGES
    ? API_AUTH_MESSAGES[code as ApiAuthErrorCode]
    : CLIENT_AUTH_MESSAGES[code as keyof typeof CLIENT_AUTH_MESSAGES]
}

function buildLoginGuidance(
  code: AuthErrorCode,
  context: LoginAuthContext,
  passphraseHadEdgeWhitespace: boolean,
): string[] {
  if (code === API_AUTH_ERROR_CODES.AUTH_INVALID_PASSPHRASE) {
    if (passphraseHadEdgeWhitespace) {
      return [LOGIN_EDGE_WHITESPACE_TIP]
    }
    if (context.multiWallet) {
      return ["Make sure you chose the right wallet."]
    }
    return []
  }

  if (code === API_AUTH_ERROR_CODES.AUTH_WALLET_NOT_FOUND) {
    return [
      "Confirm you are using the same node address as at setup.",
      "Pick a wallet from the list on this node.",
    ]
  }

  if (code === CLIENT_AUTH_ERROR_CODES.NETWORK_ERROR) {
    return ["Make sure OctoBot is running, then reload this page."]
  }

  if (code === CLIENT_AUTH_ERROR_CODES.DEVICE_STORAGE_BLOCKED) {
    return ["Allow site data and storage for this site in your browser settings."]
  }

  return []
}

export function applyLoginAuthPresentation(
  code: AuthErrorCode,
  context: LoginAuthContext,
  passphraseHadEdgeWhitespace: boolean,
): AuthErrorPresentation {
  const base = getAuthErrorPresentation(code)
  const explanation =
    code === API_AUTH_ERROR_CODES.AUTH_INVALID_PASSPHRASE &&
    passphraseHadEdgeWhitespace
      ? INVALID_PASSPHRASE_EXPLANATION_WITH_EDGE_WHITESPACE
      : base.explanation

  return {
    ...base,
    explanation,
    guidance: buildLoginGuidance(code, context, passphraseHadEdgeWhitespace),
  }
}

export function formatAuthErrorForForm(presentation: AuthErrorPresentation): string {
  const lines = [presentation.title]
  if (presentation.explanation.trim().length > 0) {
    lines.push(presentation.explanation)
  }
  for (const item of presentation.guidance) {
    lines.push(`• ${item}`)
  }
  return lines.join("\n")
}

export function resolveLoginAuthPresentation(
  error: unknown,
  passphrase: string,
  context: LoginAuthContext = { multiWallet: false },
): AuthErrorPresentation {
  const passphraseHadEdgeWhitespace = passphraseHasEdgeWhitespace(passphrase)

  if (error instanceof Error && error.message === "Authentication failed") {
    return applyLoginAuthPresentation(
      API_AUTH_ERROR_CODES.AUTH_INVALID_PASSPHRASE,
      context,
      passphraseHadEdgeWhitespace,
    )
  }

  if (!(error instanceof ApiError)) {
    return applyLoginAuthPresentation(
      CLIENT_AUTH_ERROR_CODES.DEVICE_STORAGE_BLOCKED,
      context,
      false,
    )
  }

  if (error.status === 503) {
    const code = parseAuthErrorCodeFromApiError(error)
    if (code === API_AUTH_ERROR_CODES.AUTH_NODE_NOT_CONFIGURED) {
      return applyLoginAuthPresentation(code, context, false)
    }
    return applyLoginAuthPresentation(
      CLIENT_AUTH_ERROR_CODES.NETWORK_ERROR,
      context,
      false,
    )
  }

  if (error.status === 429) {
    return LOGIN_RATE_LIMIT_PRESENTATION
  }

  if (error.status === 401) {
    const code =
      parseAuthErrorCodeFromApiError(error) ??
      API_AUTH_ERROR_CODES.AUTH_INVALID_PASSPHRASE
    return applyLoginAuthPresentation(code, context, passphraseHadEdgeWhitespace)
  }

  return applyLoginAuthPresentation(
    CLIENT_AUTH_ERROR_CODES.NETWORK_ERROR,
    context,
    false,
  )
}

/** Login form handles these inline; avoid duplicate Sonner toasts. */
export function shouldSuppressLoginErrorToast(error: unknown): boolean {
  if (error instanceof Error && error.message === "Authentication failed") {
    return true
  }
  if (!(error instanceof ApiError)) {
    return true
  }
  if (error.status === 401) {
    return true
  }
  if (error.status === 429) {
    return true
  }
  if (error.status === 503) {
    const code = parseAuthErrorCodeFromApiError(error)
    return code === API_AUTH_ERROR_CODES.AUTH_NODE_NOT_CONFIGURED
  }
  return false
}

export function resolveLoginFormAuthError(
  error: unknown,
  passphrase: string,
  context?: LoginAuthContext,
): string {
  return formatAuthErrorForForm(
    resolveLoginAuthPresentation(error, passphrase, context),
  )
}

