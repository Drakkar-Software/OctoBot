import { AlertTriangle, KeyRound, Lock, LockOpen, ShieldCheck } from "lucide-react"
import { useEffect, useState } from "react"

import type { Task_Output as Task } from "@/client"
import { NodesService } from "@/client"
import { Button } from "@/components/ui/button"
import { LoadingButton } from "@/components/ui/loading-button"
import { getTemplateById } from "@/lib/meta-templates"
import { hasStoredClientKeys, loadPassword } from "@/lib/device-key"
import type { ActionRow } from "./ColumnMappingStep"

export interface EncryptStepProps {
  actions: ActionRow[]
  onImport: (tasks: Task[]) => void
  onBack: () => void
  isImporting: boolean
}

function getValidActions(actions: ActionRow[]): ActionRow[] {
  return actions.filter((action) => {
    const template = getTemplateById(action.templateId)
    if (!template) return false
    return template.params.every(
      (p) => !p.required || p.hidden || action.paramValues[p.key]?.trim(),
    )
  })
}

function buildContentString(action: ActionRow): string {
  const template = getTemplateById(action.templateId)
  const actions = template?.actionTypes.join(",") ?? ""
  return JSON.stringify({ ...action.paramValues, ACTIONS: actions })
}

export default function EncryptStep({
  actions,
  onImport,
  onBack,
  isImporting,
}: EncryptStepProps) {
  const [encryptionEnabled, setEncryptionEnabled] = useState<boolean | null>(null)
  const [envVars, setEnvVars] = useState<string[]>([])
  const [clientKeysStored, setClientKeysStored] = useState(false)
  const validActions = getValidActions(actions)

  useEffect(() => {
    NodesService.getNodeConfig()
      .then((data) => {
        const d = data as { tasks_encryption_enabled?: boolean; server_encryption_env_vars?: string[] }
        setEncryptionEnabled(d.tasks_encryption_enabled ?? false)
        setEnvVars(d.server_encryption_env_vars ?? [])
      })
      .catch(() => setEncryptionEnabled(false))
    hasStoredClientKeys().then(setClientKeysStored)
  }, [])

  const buildPlaintextTasks = (): Task[] =>
    validActions.map((action) => ({
      name: action.name,
      content: buildContentString(action),
      type: "execute_actions",
    }))

  const handleImportWithEncryption = async () => {
    const contents = validActions.map((action) =>
      buildContentString(action),
    )

    const username = localStorage.getItem("auth_username") || "node"
    const password = (await loadPassword()) ?? ""
    const res = await fetch("/api/v1/tasks/encrypt-content", {
      method: "POST",
      headers: {
        Authorization: `Basic ${btoa(`${username}:${password}`)}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ contents }),
    })

    if (!res.ok) {
      throw new Error("Encryption failed")
    }

    const encrypted: { content: string; content_metadata: string }[] = await res.json()

    const tasks: Task[] = validActions.map((action, i) => ({
      name: action.name,
      content: encrypted[i].content,
      content_metadata: encrypted[i].content_metadata,
      type: "execute_actions",
    }))

    onImport(tasks)
  }

  const handleImportWithoutEncryption = () => {
    onImport(buildPlaintextTasks())
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <p className="text-sm font-medium">
          Encrypt & Import
        </p>
        <p className="text-xs text-muted-foreground">
          Encryption adds an additional security layer by protecting all action parameters before they are stored.
        </p>
      </div>

      {encryptionEnabled === null ? (
        <p className="text-sm text-muted-foreground">Checking encryption status...</p>
      ) : encryptionEnabled ? (
        <div className="flex flex-col gap-4">
          <div className="flex items-start gap-3 rounded-lg border border-green-500/30 bg-green-500/5 p-4">
            <ShieldCheck className="size-5 text-green-500 mt-0.5 shrink-0" />
            <div>
              <p className="text-sm font-medium">Server encryption is enabled</p>
              <p className="text-xs text-muted-foreground mt-1">
                Task content will be encrypted before submission using hybrid
                encryption (AES-256-GCM + RSA-4096 + ECDSA).
              </p>
            </div>
          </div>

          {clientKeysStored ? (
            <div className="flex items-start gap-3 rounded-lg border border-green-500/30 bg-green-500/5 p-4">
              <KeyRound className="size-5 text-green-500 mt-0.5 shrink-0" />
              <div>
                <p className="text-sm font-medium">Client decryption keys configured</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Task results can be decrypted in the browser.
                </p>
              </div>
            </div>
          ) : (
            <div className="flex items-start gap-3 rounded-lg border border-yellow-500/30 bg-yellow-500/5 p-4">
              <KeyRound className="size-5 text-yellow-500 mt-0.5 shrink-0" />
              <div>
                <p className="text-sm font-medium">Client decryption keys not configured</p>
                <p className="text-xs text-muted-foreground mt-1">
                  You can still import encrypted tasks, but won't be able to decrypt results in the browser.
                  Configure OUTPUTS keys in Settings.
                </p>
              </div>
            </div>
          )}

          <div className="flex gap-2 justify-end">
            <Button variant="outline" onClick={onBack} disabled={isImporting}>
              Back
            </Button>
            <LoadingButton
              loading={isImporting}
              onClick={handleImportWithEncryption}
              disabled={validActions.length === 0}
            >
              <Lock className="size-3.5 mr-1.5" />
              Import {validActions.length} Action{validActions.length !== 1 ? "s" : ""}
            </LoadingButton>
          </div>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          <div className="flex items-start gap-3 rounded-lg border border-yellow-500/30 bg-yellow-500/5 p-4">
            <AlertTriangle className="size-5 text-yellow-500 mt-0.5 shrink-0" />
            <div>
              <p className="text-sm font-medium">Server encryption is not configured</p>
              <p className="text-xs text-muted-foreground mt-1">
                Set the following environment variables and restart to enable task encryption:
              </p>
              <ul className="text-xs font-mono text-muted-foreground mt-2 ml-4 list-disc space-y-0.5">
                {envVars.map((v) => (
                  <li key={v}>{v}</li>
                ))}
              </ul>
            </div>
          </div>

          {clientKeysStored ? (
            <div className="flex items-start gap-3 rounded-lg border border-green-500/30 bg-green-500/5 p-4">
              <KeyRound className="size-5 text-green-500 mt-0.5 shrink-0" />
              <div>
                <p className="text-sm font-medium">Client decryption keys configured</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Task results can be decrypted in the browser once server encryption is enabled.
                </p>
              </div>
            </div>
          ) : (
            <div className="flex items-start gap-3 rounded-lg border border-yellow-500/30 bg-yellow-500/5 p-4">
              <KeyRound className="size-5 text-yellow-500 mt-0.5 shrink-0" />
              <div>
                <p className="text-sm font-medium">Client decryption keys not configured</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Configure OUTPUTS keys in Settings to decrypt task results in the browser.
                </p>
              </div>
            </div>
          )}

          <div className="flex gap-2 justify-end">
            <Button variant="outline" onClick={onBack} disabled={isImporting}>
              Back
            </Button>
            <LoadingButton
              loading={isImporting}
              variant="secondary"
              onClick={handleImportWithoutEncryption}
              disabled={validActions.length === 0}
            >
              <LockOpen className="size-3.5 mr-1.5" />
              Import {validActions.length} Action{validActions.length !== 1 ? "s" : ""}
            </LoadingButton>
          </div>
        </div>
      )}
    </div>
  )
}
