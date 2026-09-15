import { toast } from "sonner"

const COPY_SUCCESS_TITLE = "Copied to clipboard"
const COPY_FAILURE_TITLE = "Could not copy to clipboard"
const COPY_FAILURE_DESCRIPTION =
  "Your browser blocked clipboard access. Select the text and copy it manually."

const copySuccessToastOptions = (description: string) => ({
  description,
  classNames: {
    description: "font-mono text-xs break-all",
  },
})

async function writeTextToSystemClipboard(text: string): Promise<void> {
  if (!navigator.clipboard?.writeText) {
    throw new Error("Clipboard API unavailable")
  }
  await navigator.clipboard.writeText(text)
}

export function copyTextToClipboard(text: string, description: string): void {
  void writeTextToSystemClipboard(text)
    .then(() => {
      toast.success(COPY_SUCCESS_TITLE, copySuccessToastOptions(description))
    })
    .catch((error: unknown) => {
      console.error("copyTextToClipboard failed", error)
      toast.error(COPY_FAILURE_TITLE, {
        description: COPY_FAILURE_DESCRIPTION,
      })
    })
}
