import type { AuthErrorPresentation } from "@/lib/auth-error-messages"

export const LOGIN_AUTH_ERROR_SUMMARY_ID = "login-auth-error-summary"
export const LOGIN_AUTH_ERROR_TIPS_ID = "login-auth-error-tips"

function tipsHeading(guidanceCount: number): string {
  return guidanceCount === 1 ? "Tip" : "What you can try"
}

type LoginAuthErrorDisplayProps = {
  presentation: AuthErrorPresentation | null
}

export function loginAuthFieldDescribedBy(
  presentation: AuthErrorPresentation | null,
): string | undefined {
  if (!presentation) {
    return undefined
  }
  const ids = [LOGIN_AUTH_ERROR_SUMMARY_ID]
  if (presentation.guidance.length > 0) {
    ids.push(LOGIN_AUTH_ERROR_TIPS_ID)
  }
  return ids.join(" ")
}

export function LoginAuthErrorDisplay({
  presentation,
}: LoginAuthErrorDisplayProps) {
  if (!presentation) {
    return null
  }

  return (
    <div className="flex flex-col gap-3">
      <div
        id={LOGIN_AUTH_ERROR_SUMMARY_ID}
        data-testid="login-auth-error"
        role="alert"
        aria-live="polite"
        className="space-y-1"
      >
        <p className="text-sm font-medium text-destructive">
          {presentation.title}
        </p>
        {presentation.explanation.trim().length > 0 ? (
          <p className="text-sm text-destructive/90">{presentation.explanation}</p>
        ) : null}
      </div>
      {presentation.guidance.length > 0 ? (
        <div
          id={LOGIN_AUTH_ERROR_TIPS_ID}
          data-testid="login-auth-tips"
          className="rounded-lg border border-border bg-muted/40 p-3"
        >
          <p className="mb-2 text-sm font-medium">
            {tipsHeading(presentation.guidance.length)}
          </p>
          <ul className="list-disc space-y-1 pl-4 text-sm text-muted-foreground">
            {presentation.guidance.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  )
}
