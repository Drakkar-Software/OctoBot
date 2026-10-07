import type { InputHTMLAttributes, TextareaHTMLAttributes } from "react"

/**
 * HTML input/textarea props that discourage browser spellcheck, autocorrect, and
 * autofill heuristics on crypto secrets (seeds, private keys). Browsers and
 * extensions may still apply their own behavior.
 */
export const cryptoSecretInputProps = {
  spellCheck: false,
  autoComplete: "off",
  autoCorrect: "off",
  autoCapitalize: "none",
} as const satisfies Pick<
  InputHTMLAttributes<HTMLInputElement>,
  "spellCheck" | "autoComplete" | "autoCorrect" | "autoCapitalize"
>

export type CryptoSecretInputProps = typeof cryptoSecretInputProps

export function cryptoSecretTextareaProps(): Pick<
  TextareaHTMLAttributes<HTMLTextAreaElement>,
  "spellCheck" | "autoComplete" | "autoCorrect" | "autoCapitalize"
> {
  return cryptoSecretInputProps
}
