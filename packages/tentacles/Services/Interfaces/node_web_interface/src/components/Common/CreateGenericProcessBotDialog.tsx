import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useNavigate } from "@tanstack/react-router"
import { TriangleAlert } from "lucide-react"
import { useState } from "react"

import { OctobotsService } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { LoadingButton } from "@/components/ui/loading-button"
import {
  buildCreateGenericProcessBotRequestBody,
  formatCreateGenericProcessBotError,
  validateCreateGenericProcessBotName,
} from "@/lib/octobots/create-generic-process-bot"

type DialogStep = "form" | "success"

interface CreateGenericProcessBotDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function CreateGenericProcessBotDialog({
  open,
  onOpenChange,
}: CreateGenericProcessBotDialogProps) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [step, setStep] = useState<DialogStep>("form")
  const [name, setName] = useState("")
  const [createdBotName, setCreatedBotName] = useState("")
  const [inlineError, setInlineError] = useState<string | null>(null)
  const [nameValidationMessage, setNameValidationMessage] = useState<
    string | null
  >(null)

  const createMutation = useMutation({
    mutationFn: (trimmedName: string) =>
      OctobotsService.createGenericProcessBot({
        requestBody: buildCreateGenericProcessBotRequestBody(trimmedName),
      }),
    onSuccess: (_result, trimmedName) => {
      setCreatedBotName(trimmedName)
      setStep("success")
      setInlineError(null)
      queryClient.invalidateQueries({ queryKey: ["tasks"] })
    },
    onError: (error) => {
      setInlineError(formatCreateGenericProcessBotError(error))
    },
  })

  const resetDialog = () => {
    setStep("form")
    setName("")
    setCreatedBotName("")
    setInlineError(null)
    setNameValidationMessage(null)
    createMutation.reset()
  }

  const handleOpenChange = (nextOpen: boolean) => {
    if (!nextOpen) {
      resetDialog()
    }
    onOpenChange(nextOpen)
  }

  const handleNameChange = (value: string) => {
    setName(value)
    setInlineError(null)
    if (nameValidationMessage !== null) {
      setNameValidationMessage(null)
    }
  }

  const handleCreate = () => {
    const validation = validateCreateGenericProcessBotName(name)
    if (!validation.valid) {
      setNameValidationMessage(validation.message)
      return
    }
    setNameValidationMessage(null)
    createMutation.mutate(validation.trimmedName)
  }

  const handleBackToOctoBots = () => {
    handleOpenChange(false)
    navigate({ to: "/" })
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        {step === "form" ? (
          <>
            <DialogHeader>
              <DialogTitle>Name your OctoBot</DialogTitle>
              <DialogDescription>
                This starts an OctoBot you can configure manually with its
                dedicated interface. Best for backtesting and in-depth analysis.
              </DialogDescription>
            </DialogHeader>
            <div className="flex flex-col gap-3">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="generic-process-bot-name">Bot name</Label>
                <Input
                  id="generic-process-bot-name"
                  value={name}
                  onChange={(event) => handleNameChange(event.target.value)}
                  placeholder="My manual OctoBot"
                  maxLength={200}
                  autoFocus
                />
                {nameValidationMessage && (
                  <p className="text-xs text-neg">{nameValidationMessage}</p>
                )}
              </div>
              {inlineError && (
                <div className="flex items-start gap-2 rounded-md border border-neg/25 border-l-2 border-l-neg/70 bg-neg/[0.07] px-2.5 py-1.5">
                  <TriangleAlert className="mt-0.5 size-3.5 shrink-0 text-neg/80" />
                  <p className="text-xs leading-snug text-neg/75">
                    {inlineError}
                  </p>
                </div>
              )}
            </div>
            <DialogFooter>
              <DialogClose asChild>
                <Button
                  variant="outline"
                  disabled={createMutation.isPending}
                >
                  Cancel
                </Button>
              </DialogClose>
              <LoadingButton
                loading={createMutation.isPending}
                disabled={name.trim().length === 0}
                onClick={handleCreate}
              >
                Create OctoBot
              </LoadingButton>
            </DialogFooter>
          </>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>OctoBot created</DialogTitle>
              <DialogDescription>
                <span className="font-medium text-foreground">
                  {createdBotName}
                </span>{" "}
                is starting. You can configure it from the OctoBots list once it
                is ready.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button onClick={handleBackToOctoBots}>Back to OctoBots</Button>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
