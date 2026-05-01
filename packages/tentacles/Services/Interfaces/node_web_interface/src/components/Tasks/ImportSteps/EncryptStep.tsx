import { AlertTriangle, KeyRound, Lock, LockOpen, ShieldCheck } from "lucide-react"
import { useEffect, useState } from "react"

import type { Task_Input as Task } from "@/client"
import { NodesService } from "@/client"
import { Button } from "@/components/ui/button"
import { LoadingButton } from "@/components/ui/loading-button"
import { isParamValueValid } from "@/lib/action-templates"
import { getTemplateById } from "@/lib/meta-templates"
import { hasStoredClientKeys, loadClientKeys } from "@/lib/device-key"
import { encryptAndSign, derivePublicPemsFromPrivates } from "@/lib/client-encryption"
import type { ClientKeys } from "@/lib/client-encryption"
import { fetchServerPublicKeys } from "@/lib/server-keys"
import useCustomToast from "@/hooks/useCustomToast"
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
      (p) => !p.required || p.hidden || isParamValueValid(p, action.paramValues[p.key]),
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
  const { showErrorToast } = useCustomToast()

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
    try {
      const clientKeys = await loadClientKeys()
      if (!clientKeys) throw new Error("Browser keys not configured — add them in Settings")
      const serverKeys = await fetchServerPublicKeys()
      const { ecdsa_public_pem } = await derivePublicPemsFromPrivates(clientKeys as ClientKeys)
      const tasks: Task[] = await Promise.all(
        validActions.map(async (action) => {
          const { content, content_metadata } = await encryptAndSign(
            buildContentString(action),
            clientKeys as ClientKeys,
            serverKeys.rsa_public,
          )
          return {
            name: action.name,
            content,
            content_metadata,
            type: "execute_actions",
            user_ecdsa_public_key: ecdsa_public_pem,
          }
        }),
      )
      onImport(tasks)
    } catch (err) {
      showErrorToast(err instanceof Error ? err.message : "Encryption failed")
    }
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
                  Task will be imported without encryption. Configure browser keys in Settings to enable encrypted import.
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
              onClick={clientKeysStored ? handleImportWithEncryption : handleImportWithoutEncryption}
              variant={clientKeysStored ? "default" : "secondary"}
              disabled={validActions.length === 0}
            >
              {clientKeysStored ? <Lock className="size-3.5 mr-1.5" /> : <LockOpen className="size-3.5 mr-1.5" />}
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
                  Configure browser keys in Settings to decrypt task results in the browser.
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
