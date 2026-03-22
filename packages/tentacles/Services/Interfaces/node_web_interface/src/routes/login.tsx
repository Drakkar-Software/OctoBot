import { zodResolver } from "@hookform/resolvers/zod"
import {
  createFileRoute,
  redirect,
} from "@tanstack/react-router"
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
import useAuth, { isLoggedIn } from "@/hooks/useAuth"

const formSchema = z.object({
  passphrase: z.string().min(1, { message: "Passphrase is required" }),
})

type FormData = z.infer<typeof formSchema>

export const Route = createFileRoute("/login")({
  component: Login,
  beforeLoad: async () => {
    if (isLoggedIn()) {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Log In" }],
  }),
})

function Login() {
  const { loginMutation } = useAuth()
  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      passphrase: "",
    },
  })

  const onSubmit = (data: FormData) => {
    if (loginMutation.isPending) return
    // Use stored address or a placeholder — backend only checks the passphrase
    const username = localStorage.getItem("auth_username") || "node"
    loginMutation.mutate({ username, password: data.passphrase })
  }

  return (
    <AuthLayout>
      <Form {...form}>
        <form
          onSubmit={form.handleSubmit(onSubmit)}
          className="flex flex-col gap-6"
        >
          <div className="flex flex-col items-center gap-2 text-center">
            <h1 className="text-2xl font-bold">Unlock your node</h1>
            <p className="text-sm text-muted-foreground">
              Enter your passphrase to continue.
            </p>
          </div>

          <div className="grid gap-4">
            <FormField
              control={form.control}
              name="passphrase"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Passphrase</FormLabel>
                  <FormControl>
                    <PasswordInput
                      data-testid="passphrase-input"
                      placeholder="Your passphrase"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage className="text-xs" />
                </FormItem>
              )}
            />

            <LoadingButton type="submit" loading={loginMutation.isPending}>
              Unlock
            </LoadingButton>
          </div>
        </form>
      </Form>
    </AuthLayout>
  )
}
