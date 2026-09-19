import { zodResolver } from "@hookform/resolvers/zod"
import { Link, createFileRoute } from "@tanstack/react-router"
import { TriangleAlert } from "lucide-react"
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
import { LoadingButton } from "@/components/ui/loading-button"
import { PasswordInput } from "@/components/ui/password-input"
import { recoverWalletPassphrase } from "@/lib/recovery-phrase"

const formSchema = z
  .object({
    seed: z
      .string()
      .min(1, { message: "Recovery phrase is required" })
      .refine((value) => {
        const words = value.trim().split(/\s+/).filter(Boolean)
        return words.length === 12 || words.length === 24
      }, { message: "Enter a 12- or 24-word phrase" }),
    newPassphrase: z
      .string()
      .min(8, { message: "Passphrase must be at least 8 characters" }),
    confirmPassphrase: z.string().min(1, { message: "Confirm your passphrase" }),
  })
  .refine((data) => data.newPassphrase === data.confirmPassphrase, {
    message: "Passphrases do not match",
    path: ["confirmPassphrase"],
  })

type FormData = z.infer<typeof formSchema>

export const Route = createFileRoute("/login/recover")({
  component: RecoverAccount,
  head: () => ({
    meta: [{ title: "Recover account" }],
  }),
})

function RecoverAccount() {
  const [restoredAddress, setRestoredAddress] = useState<string | null>(null)

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    defaultValues: {
      seed: "",
      newPassphrase: "",
      confirmPassphrase: "",
    },
  })

  const onSubmit = async (data: FormData) => {
    form.clearErrors("seed")
    try {
      const result = await recoverWalletPassphrase(data.seed, data.newPassphrase)
      setRestoredAddress(result.address)
    } catch (error) {
      form.setError("seed", {
        message:
          error instanceof Error ? error.message : "Could not restore account",
      })
    }
  }

  if (restoredAddress) {
    return (
      <AuthLayout>
        <div className="flex flex-col gap-6 text-center">
          <h1 className="text-2xl font-bold">Account restored</h1>
          <p className="text-sm text-muted-foreground">
            Your new passphrase is set. Unlock with it on the next screen.
          </p>
          <Link
            to="/login"
            className="inline-flex h-10 items-center justify-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground"
          >
            Back to unlock
          </Link>
        </div>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout>
      <Form {...form}>
        <form
          onSubmit={form.handleSubmit(onSubmit)}
          className="flex flex-col gap-6"
        >
          <div className="flex flex-col items-center gap-2 text-center">
            <h1 className="text-2xl font-bold">Recover your account</h1>
            <p className="text-sm text-muted-foreground">
              Enter your recovery phrase and choose a new passphrase.
            </p>
            <Link
              to="/login"
              className="text-xs text-muted-foreground underline underline-offset-2"
            >
              ← Back to unlock
            </Link>
          </div>

          <div className="flex items-start gap-2 rounded-md border border-warn/30 bg-warn/10 p-3 text-sm text-warn">
            <TriangleAlert className="mt-0.5 size-4 shrink-0" />
            <span>Only enter your phrase on this device. It never leaves your node.</span>
          </div>

          <div className="grid gap-4">
            <FormField
              control={form.control}
              name="seed"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Recovery phrase</FormLabel>
                  <FormControl>
                    <textarea
                      data-testid="recovery-phrase-input"
                      placeholder="word1 word2 word3 …"
                      rows={4}
                      className="w-full rounded-md border border-rule bg-input px-3 py-2 text-sm font-mono text-foreground focus:outline-none focus:ring-1 focus:ring-frost resize-none"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage className="text-xs" />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="newPassphrase"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>New passphrase</FormLabel>
                  <FormControl>
                    <PasswordInput
                      data-testid="new-passphrase-input"
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
                  <FormLabel>Confirm passphrase</FormLabel>
                  <FormControl>
                    <PasswordInput
                      data-testid="confirm-passphrase-input"
                      placeholder="Repeat passphrase"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage className="text-xs" />
                </FormItem>
              )}
            />

            <LoadingButton type="submit" loading={form.formState.isSubmitting}>
              Restore account
            </LoadingButton>
          </div>
        </form>
      </Form>
    </AuthLayout>
  )
}
