import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation } from "@tanstack/react-query"
import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { type ApiError, type SetupResult, SetupService } from "@/client"
import { AuthLayout } from "@/components/Common/AuthLayout"
import { SetupStepHeader } from "@/components/Setup/SetupStepHeader"
import { WalletSeedOnboardingFlow } from "@/components/Wallet/WalletSeedOnboardingFlow"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"
import { PasswordInput } from "@/components/ui/password-input"
import { clearAuth } from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"
import { savePassword } from "@/lib/device-key"
import {
  clearSetupGenerateFlow,
  markSetupGenerateFlow,
  SETUP_STEP_TOTAL_GENERATE,
  SETUP_STEP_TOTAL_IMPORT,
} from "@/lib/seed-onboarding"
import { fetchSeedAfterWalletCreate } from "@/lib/wallet-seed-after-create"
import { handleError } from "@/utils"

export const Route = createFileRoute("/setup/")({
  component: SetupWallet,
  head: () => ({
    meta: [{ title: "Setup - Set up your wallet" }],
  }),
})

const baseSchema = z.object({
  name: z.string().optional(),
  passphrase: z
    .string()
    .min(8, { message: "Passphrase must be at least 8 characters" }),
  confirmPassphrase: z.string(),
})

const generateSchema = baseSchema.refine(
  (d) => d.passphrase === d.confirmPassphrase,
  { message: "Passphrases do not match", path: ["confirmPassphrase"] },
)

const importSchema = baseSchema
  .extend({
    privateKey: z.string().regex(/^(0x)?[0-9a-fA-F]{64}$/, {
      message: "Must be a valid 64-hex-char EVM private key",
    }),
  })
  .refine((d) => d.passphrase === d.confirmPassphrase, {
    message: "Passphrases do not match",
    path: ["confirmPassphrase"],
  })

type GenerateData = z.infer<typeof generateSchema>
type ImportData = z.infer<typeof importSchema>

function NodeWalletNote() {
  return (
    <div className="rounded-md border bg-muted/50 p-3 text-sm text-muted-foreground">
      <span className="font-medium text-foreground">About your Node wallet:</span>{" "}
      Your Node is secured by its own cryptographic wallet. It is independent
      from any cryptocurrency wallet you might already have.
    </div>
  )
}

function SetupWallet() {
  const navigate = useNavigate()
  const [mode, setMode] = useState<"generate" | "import">("generate")
  const [generatedSeed, setGeneratedSeed] = useState<string | null>(null)
  const { showErrorToast } = useCustomToast()

  const finishSetupNavigation = () => {
    navigate({ to: "/setup/connect" })
  }

  const generateForm = useForm<GenerateData>({
    resolver: zodResolver(generateSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: { name: "", passphrase: "", confirmPassphrase: "" },
  })

  const importForm = useForm<ImportData>({
    resolver: zodResolver(importSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      name: "",
      passphrase: "",
      confirmPassphrase: "",
      privateKey: "",
    },
  })

  const initMutation = useMutation<
    SetupResult,
    ApiError,
    { passphrase: string; privateKey?: string; name?: string }
  >({
    mutationFn: ({ passphrase, privateKey, name }) =>
      SetupService.initSetup({
        requestBody: {
          passphrase,
          node_type: "standalone",
          private_key: privateKey || undefined,
          name: name?.trim() || undefined,
        },
      }),
    onSuccess: async (result, { passphrase, name, privateKey }) => {
      try {
        await savePassword(passphrase)
      } catch {
        showErrorToast(
          "Could not save your passphrase on this device. Check your browser's privacy settings and try again.",
        )
        return
      }
      localStorage.setItem("auth_username", result.address)
      if (name?.trim()) {
        localStorage.setItem("auth_wallet_name", name.trim())
      }
      sessionStorage.setItem("setup_in_progress", "true")

      if (privateKey) {
        clearSetupGenerateFlow()
        finishSetupNavigation()
        return
      }

      try {
        const seed = await fetchSeedAfterWalletCreate(result.address, passphrase)
        if (seed) {
          setGeneratedSeed(seed)
          return
        }
      } catch {
        showErrorToast(
          "Your wallet was created but the seed phrase could not be loaded. Export it from Settings after setup.",
        )
      }
      clearSetupGenerateFlow()
      finishSetupNavigation()
    },
    onError: async (error) => {
      const apiError = error as ApiError
      if (apiError.status === 409) {
        sessionStorage.removeItem("setup_in_progress")
        await clearAuth()
        navigate({ to: "/login" })
        return
      }
      handleError.bind(showErrorToast)(apiError)
    },
  })

  const onGenerateSubmit = (data: GenerateData) => {
    initMutation.mutate({ passphrase: data.passphrase, name: data.name })
  }

  const onImportSubmit = (data: ImportData) => {
    initMutation.mutate({
      passphrase: data.passphrase,
      privateKey: data.privateKey,
      name: data.name,
    })
  }

  const handleSeedOnboardingComplete = () => {
    markSetupGenerateFlow()
    setGeneratedSeed(null)
    finishSetupNavigation()
  }

  if (generatedSeed) {
    return (
      <AuthLayout>
        <WalletSeedOnboardingFlow
          seed={generatedSeed}
          revealStep={2}
          quizStep={3}
          totalSteps={SETUP_STEP_TOTAL_GENERATE}
          onComplete={handleSeedOnboardingComplete}
        />
      </AuthLayout>
    )
  }

  const setupTotal =
    mode === "generate" ? SETUP_STEP_TOTAL_GENERATE : SETUP_STEP_TOTAL_IMPORT

  return (
    <AuthLayout>
      <div className="flex flex-col gap-6">
        <SetupStepHeader
          step={1}
          total={setupTotal}
          title="Set up your wallet"
          subtitle="Create a new wallet or import an existing one."
        />

        <div className="flex rounded-md border text-sm">
          <button
            type="button"
            onClick={() => setMode("generate")}
            className={`flex-1 rounded-l-md px-4 py-2 transition-colors ${
              mode === "generate"
                ? "bg-primary text-primary-foreground"
                : "hover:bg-muted"
            }`}
          >
            Generate new
          </button>
          <button
            type="button"
            onClick={() => setMode("import")}
            className={`flex-1 rounded-r-md px-4 py-2 transition-colors ${
              mode === "import"
                ? "bg-primary text-primary-foreground"
                : "hover:bg-muted"
            }`}
          >
            Import existing
          </button>
        </div>

        {mode === "generate" ? (
          <Form key="generate" {...generateForm}>
            <form
              onSubmit={generateForm.handleSubmit(onGenerateSubmit)}
              className="flex flex-col gap-4"
            >
              <FormField
                control={generateForm.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>
                      Wallet name{" "}
                      <span className="text-muted-foreground font-normal">
                        (optional)
                      </span>
                    </FormLabel>
                    <FormControl>
                      <Input placeholder="e.g. My node" {...field} />
                    </FormControl>
                    <FormMessage className="text-xs" />
                  </FormItem>
                )}
              />
              <FormField
                control={generateForm.control}
                name="passphrase"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Passphrase</FormLabel>
                    <FormControl>
                      <PasswordInput
                        placeholder="Min. 8 characters"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage className="text-xs" />
                  </FormItem>
                )}
              />
              <FormField
                control={generateForm.control}
                name="confirmPassphrase"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Confirm passphrase</FormLabel>
                    <FormControl>
                      <PasswordInput
                        placeholder="Repeat passphrase"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage className="text-xs" />
                  </FormItem>
                )}
              />
              <NodeWalletNote />
              <LoadingButton type="submit" loading={initMutation.isPending}>
                Generate wallet
              </LoadingButton>
            </form>
          </Form>
        ) : (
          <Form key="import" {...importForm}>
            <form
              onSubmit={importForm.handleSubmit(onImportSubmit)}
              className="flex flex-col gap-4"
            >
              <FormField
                control={importForm.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>
                      Wallet name{" "}
                      <span className="text-muted-foreground font-normal">
                        (optional)
                      </span>
                    </FormLabel>
                    <FormControl>
                      <Input placeholder="e.g. My node" {...field} />
                    </FormControl>
                    <FormMessage className="text-xs" />
                  </FormItem>
                )}
              />
              <FormField
                control={importForm.control}
                name="privateKey"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Private key</FormLabel>
                    <FormControl>
                      <Input
                        type="password"
                        placeholder="0x... or 64 hex characters"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage className="text-xs" />
                  </FormItem>
                )}
              />
              <FormField
                control={importForm.control}
                name="passphrase"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Passphrase</FormLabel>
                    <FormControl>
                      <PasswordInput
                        placeholder="Min. 8 characters"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage className="text-xs" />
                  </FormItem>
                )}
              />
              <FormField
                control={importForm.control}
                name="confirmPassphrase"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Confirm passphrase</FormLabel>
                    <FormControl>
                      <PasswordInput
                        placeholder="Repeat passphrase"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage className="text-xs" />
                  </FormItem>
                )}
              />
              <NodeWalletNote />
              <LoadingButton type="submit" loading={initMutation.isPending}>
                Continue
              </LoadingButton>
            </form>
          </Form>
        )}
      </div>
    </AuthLayout>
  )
}
