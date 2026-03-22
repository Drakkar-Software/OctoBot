import { zodResolver } from "@hookform/resolvers/zod"
import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { AuthLayout } from "@/components/Common/AuthLayout"
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

export const Route = createFileRoute("/setup/")({
  component: SetupWallet,
  head: () => ({
    meta: [{ title: "Setup — Step 1" }],
  }),
})

const baseSchema = z.object({
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
    privateKey: z
      .string()
      .regex(/^(0x)?[0-9a-fA-F]{64}$/, { message: "Must be a valid 64-hex-char EVM private key" }),
  })
  .refine((d) => d.passphrase === d.confirmPassphrase, {
    message: "Passphrases do not match",
    path: ["confirmPassphrase"],
  })

type GenerateData = z.infer<typeof generateSchema>
type ImportData = z.infer<typeof importSchema>

function SetupWallet() {
  const navigate = useNavigate()
  const [mode, setMode] = useState<"generate" | "import">("generate")

  const generateForm = useForm<GenerateData>({
    resolver: zodResolver(generateSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: { passphrase: "", confirmPassphrase: "" },
  })

  const importForm = useForm<ImportData>({
    resolver: zodResolver(importSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: { passphrase: "", confirmPassphrase: "", privateKey: "" },
  })

  const onGenerateSubmit = (data: GenerateData) => {
    sessionStorage.setItem("setup_passphrase", data.passphrase)
    sessionStorage.removeItem("setup_private_key")
    navigate({ to: "/setup/node-type" })
  }

  const onImportSubmit = (data: ImportData) => {
    sessionStorage.setItem("setup_passphrase", data.passphrase)
    sessionStorage.setItem("setup_private_key", data.privateKey)
    navigate({ to: "/setup/node-type" })
  }

  return (
    <AuthLayout>
      <div className="flex flex-col gap-6">
        <div className="flex flex-col items-center gap-2 text-center">
          <p className="text-xs text-muted-foreground">Step 1 / 3</p>
          <h1 className="text-2xl font-bold">Secure your node</h1>
          <p className="text-sm text-muted-foreground">
            Your wallet is your node's cryptographic identity.
          </p>
        </div>

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
          <Form {...generateForm}>
            <form
              onSubmit={generateForm.handleSubmit(onGenerateSubmit)}
              className="flex flex-col gap-4"
            >
              <FormField
                control={generateForm.control}
                name="passphrase"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Passphrase</FormLabel>
                    <FormControl>
                      <PasswordInput placeholder="Min. 8 characters" {...field} />
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
                      <PasswordInput placeholder="Repeat passphrase" {...field} />
                    </FormControl>
                    <FormMessage className="text-xs" />
                  </FormItem>
                )}
              />
              <LoadingButton type="submit">
                Continue
              </LoadingButton>
            </form>
          </Form>
        ) : (
          <Form {...importForm}>
            <form
              onSubmit={importForm.handleSubmit(onImportSubmit)}
              className="flex flex-col gap-4"
            >
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
                      <PasswordInput placeholder="Min. 8 characters" {...field} />
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
                      <PasswordInput placeholder="Repeat passphrase" {...field} />
                    </FormControl>
                    <FormMessage className="text-xs" />
                  </FormItem>
                )}
              />
              <LoadingButton type="submit">
                Continue
              </LoadingButton>
            </form>
          </Form>
        )}
      </div>
    </AuthLayout>
  )
}
