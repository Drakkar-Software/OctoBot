import { createContext, type ReactNode, useContext, useState } from "react"

const STORAGE_KEY = "octobot-client-demo:node-url"

type NodeUrlContextValue = {
  url: string
  setUrl: (url: string) => void
}

// One node URL, shared by every panel that needs to reach a real node
// (connect/queue, mint a read-only pairing) — entering it once in either
// place fills in the other, same as the shared wallet key. Persisted to
// localStorage: unlike the wallet key, a node's address isn't a secret,
// and retyping a tailnet hostname every reload is real friction.
const NodeUrlContext = createContext<NodeUrlContextValue | null>(null)

export function NodeUrlProvider({ children }: { children: ReactNode }) {
  const [url, setUrlState] = useState(() => {
    try {
      return localStorage.getItem(STORAGE_KEY) ?? ""
    } catch {
      return ""
    }
  })
  const setUrl = (next: string) => {
    setUrlState(next)
    try {
      localStorage.setItem(STORAGE_KEY, next)
    } catch {
      // Private browsing / storage disabled — the demo still works, it just
      // won't remember the url across a reload.
    }
  }
  return (
    <NodeUrlContext.Provider value={{ url, setUrl }}>
      {children}
    </NodeUrlContext.Provider>
  )
}

export function useNodeUrl(): NodeUrlContextValue {
  const ctx = useContext(NodeUrlContext)
  if (!ctx) throw new Error("useNodeUrl must be used within a NodeUrlProvider")
  return ctx
}
