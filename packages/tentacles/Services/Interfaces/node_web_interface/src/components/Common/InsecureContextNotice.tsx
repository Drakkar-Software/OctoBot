import { getLoopbackUrl } from "@/lib/secure-context"

const InsecureContextNotice = () => {
  const loopbackUrl = getLoopbackUrl(window.location.href)

  return (
    <div
      className="flex min-h-screen items-center justify-center flex-col p-4"
      data-testid="insecure-context-notice"
    >
      <div className="flex flex-col items-center justify-center p-4 max-w-md text-center">
        <span className="text-6xl md:text-8xl font-bold leading-none mb-4">
          🔒
        </span>
        <h1 className="text-2xl font-bold mb-2">Secure context required</h1>
        <p className="text-lg text-muted-foreground mb-4">
          This browser origin does not support the cryptography the node needs.
          Open the node UI from a secure address instead.
        </p>
        {loopbackUrl ? (
          <p className="text-sm text-muted-foreground mb-6">
            <a
              href={loopbackUrl}
              className="underline underline-offset-2 text-foreground"
            >
              {loopbackUrl}
            </a>
          </p>
        ) : (
          <p className="text-sm text-muted-foreground mb-6">
            On this machine, open{" "}
            <span className="font-mono text-foreground">
              http://127.0.0.1:{window.location.port || "8000"}/app
            </span>
            . To reach the node from another device, serve it over HTTPS.
          </p>
        )}
      </div>
    </div>
  )
}

export default InsecureContextNotice
