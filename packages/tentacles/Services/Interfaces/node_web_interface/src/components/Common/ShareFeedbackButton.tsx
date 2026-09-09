import type { VariantProps } from "class-variance-authority"
import { MessageSquare } from "lucide-react"
import { useState } from "react"

import { ShareFeedbackDialog } from "@/components/Common/ShareFeedbackDialog"
import { Button, buttonVariants } from "@/components/ui/button"
import type { ShareFeedbackContext } from "@/lib/feedback-share"

type ShareFeedbackButtonProps = {
  context: ShareFeedbackContext
  variant?: VariantProps<typeof buttonVariants>["variant"]
  size?: VariantProps<typeof buttonVariants>["size"]
}

export function ShareFeedbackButton({
  context,
  variant = "outline",
  size,
}: ShareFeedbackButtonProps) {
  const [open, setOpen] = useState(false)

  return (
    <>
      <Button
        type="button"
        variant={variant}
        size={size}
        onClick={() => setOpen(true)}
      >
        <MessageSquare className="size-4" />
        <span className="hidden sm:inline">Share feedback</span>
      </Button>
      <ShareFeedbackDialog
        open={open}
        onOpenChange={setOpen}
        context={context}
      />
    </>
  )
}
