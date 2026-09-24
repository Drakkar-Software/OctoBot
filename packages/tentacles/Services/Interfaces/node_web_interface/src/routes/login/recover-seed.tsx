import { zodResolver } from "@hookform/resolvers/zod"
import { createFileRoute, Link, redirect, useNavigate } from "@tanstack/react-router"
import { TriangleAlert } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { SetupService } from "@/client"
import { AuthLayout } from "@/components/Common/AuthLayout"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { LoadingButton } from "@/components/ui/loading-button"
import { PasswordInput } from "@/components/ui/password-input"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { isLoggedIn } from "@/hooks/useAuth"
import { markLoginPassphraseRecoverySuccess } from "@/lib/login-passphrase-recovery-hint"
import { resolveRecoverSeedSubmitError } from "@/lib/passphrase-recovery-errors"
import type { PassphraseRecoveryProofMode } from "@/lib/passphrase-recovery-validation"
import { cryptoSecretTextareaProps } from "@/lib/crypto-secret-input"
import { truncateAddress } from "@/lib/wallet-utils"

const searchSchema = z.object({
  address: z.string().min(1),
})

const baseSchema = z.object({
  newPassphrase: z
    .string()
    .min(8, { message: "Passphrase must be at least 8 characters" }),
  confirmPassphrase: z.string(),
  seed: z.string().optional(),
  privateKey: z.string().optional(),
})

const formSchema = baseSchema
  .refine((data) => data.newPassphrase === data.confirmPassphrase, {
    message: "Passphrases do not match",
    path: ["confirmPassphrase"],
  })
  .superRefine((data, ctx) => {
    const mode: PassphraseRecoveryProofMode | null = data.privateKey?.trim()
      ? "hex"
      : data.seed?.trim()
        ? "seed"
        : null
    if (mode === "hex") {
      if (!/^(0x)?[0-9a-fA-F]{64}$/.test(data.privateKey?.trim() ?? "")) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Must be a valid 64-hex-char EVM private key",
          path: ["privateKey"],
        })
      }
    } else if (mode === "seed") {
      const words = (data.seed?.trim() ?? "").split(/\s+/).filter(Boolean)
      if (words.length < 12) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Enter your full seed phrase (at least 12 words)",
          path: ["seed"],
        })
      }
    } else {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: "Enter your seed phrase or private key",
        path: ["seed"],
      })
    }
  })

type FormData = z.infer<typeof formSchema>

export const Route = createFileRoute("/login/recover-seed")({
  validateSearch: searchSchema,
  beforeLoad: ({ search }) => {
    if (!search.address?.trim()) {
      throw redirect({ to: "/login" })
    }
  },
  component: RecoverPassphrase,
  head: () => ({
    meta: [{ title: "Recover passphrase" }],
  }),
})

function RecoverPassphrase() {
  const navigate = useNavigate()
  const { address } = Route.useSearch()
  const [proofMode, setProofMode] = useState<PassphraseRecoveryProofMode>("seed")
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [unavailable, setUnavailable] = useState(false)

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    defaultValues: {
      newPassphrase: "",
      confirmPassphrase: "",
      seed: "",
      privateKey: "",
    },
  })

  const onSubmit = async (data: FormData) => {
    setSubmitError(null)
    setUnavailable(false)
    try {
      await SetupService.recoverWalletFromSeedRoute({
        requestBody: {
          address: address.trim(),
          new_passphrase: data.newPassphrase,
          seed: proofMode === "seed" ? data.seed?.trim() : null,
          private_key: proofMode === "hex" ? data.privateKey?.trim() : null,
        },
      })
      markLoginPassphraseRecoverySuccess()
      await navigate({ to: "/login" })
    } catch (error) {
      const { message, unavailable: recoveryUnavailable } =
        resolveRecoverSeedSubmitError(error)
      setUnavailable(recoveryUnavailable)
      setSubmitError(message)
    }
  }

  return (
    <AuthLayout>
      <Form {...form}>
        <form
          onSubmit={form.handleSubmit(onSubmit)}
          className="flex flex-col gap-6"
          data-testid="recover-passphrase-form"
        >
          <div className="flex flex-col items-center gap-2 text-center">
            <h1 className="text-2xl font-bold">Reset wallet passphrase</h1>
            <p
              className="text-xs font-mono text-muted-foreground"
              data-testid="recover-wallet-address"
            >
              {truncateAddress(address)}
            </p>
          </div>

          <div
            className="rounded-md border border-amber-500/40 bg-amber-500/10 p-3 text-sm text-muted-foreground"
            role="note"
          >
            <div className="flex gap-2">
              <TriangleAlert className="size-4 shrink-0 text-amber-600" />
              <p>
                This replaces the passphrase for this wallet on this node. You
                will need the new passphrase to unlock.
              </p>
            </div>
          </div>

          {unavailable ? (
            <div
              className="rounded-lg border border-destructive/40 bg-destructive/10 p-3 text-sm"
              data-testid="recover-unavailable-banner"
              role="alert"
            >
              <p className="font-medium text-foreground">Recovery unavailable</p>
              <p className="text-muted-foreground">{submitError}</p>
            </div>
          ) : null}

          <Tabs
            value={proofMode}
            onValueChange={(value) => {
              const mode = value as PassphraseRecoveryProofMode
              setProofMode(mode)
              setSubmitError(null)
              form.setValue("seed", "")
              form.setValue("privateKey", "")
            }}
          >
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="seed" data-testid="recover-proof-tab-seed">
                Seed phrase
              </TabsTrigger>
              <TabsTrigger value="hex" data-testid="recover-proof-tab-hex">
                Private key
              </TabsTrigger>
            </TabsList>
            <TabsContent value="seed" className="mt-4">
              <FormField
                control={form.control}
                name="seed"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Seed phrase</FormLabel>
                    <FormControl>
                      <textarea
                        data-testid="recover-seed-input"
                        className="flex min-h-[100px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                        placeholder="To prove you own the wallet, enter your 12 or 24 word seed phrase"
                        {...cryptoSecretTextareaProps()}
                        {...field}
                        onChange={(event) => {
                          setSubmitError(null)
                          field.onChange(event)
                        }}
                      />
                    </FormControl>
                    <FormMessage className="text-xs" />
                  </FormItem>
                )}
              />
            </TabsContent>
            <TabsContent value="hex" className="mt-4">
              <FormField
                control={form.control}
                name="privateKey"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Private key (hex)</FormLabel>
                    <FormControl>
                      <textarea
                        data-testid="recover-hex-input"
                        className="flex min-h-[80px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm font-mono shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                        placeholder="To prove you own the wallet, enter your 64-character hex private key"
                        {...cryptoSecretTextareaProps()}
                        {...field}
                        onChange={(event) => {
                          setSubmitError(null)
                          field.onChange(event)
                        }}
                      />
                    </FormControl>
                    <FormMessage className="text-xs" />
                  </FormItem>
                )}
              />
            </TabsContent>
          </Tabs>

          <div className="grid gap-4">
            <FormField
              control={form.control}
              name="newPassphrase"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>New passphrase</FormLabel>
                  <FormControl>
                    <PasswordInput
                      data-testid="recover-new-passphrase-input"
                      placeholder="At least 8 characters"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage className="text-xs" />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="confirmPassphrase"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Confirm new passphrase</FormLabel>
                  <FormControl>
                    <PasswordInput
                      data-testid="recover-confirm-passphrase-input"
                      placeholder="Repeat new passphrase"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage className="text-xs" />
                </FormItem>
              )}
            />
          </div>

          {submitError && !unavailable ? (
            <p
              className="text-sm text-destructive"
              data-testid="recover-submit-error"
              role="alert"
            >
              {submitError}
            </p>
          ) : null}

          <LoadingButton
            type="submit"
            loading={form.formState.isSubmitting}
            data-testid="recover-submit-button"
          >
            Reset passphrase
          </LoadingButton>

          <p className="text-center">
            <Link
              to="/login"
              className="text-xs text-muted-foreground underline underline-offset-2"
              data-testid="recover-back-to-unlock-link"
            >
              Back to unlock
            </Link>
          </p>
        </form>
      </Form>
    </AuthLayout>
  )
}
