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

function copyWithExecCommand(text: string): void {
  const textarea = document.createElement("textarea")
  textarea.value = text
  textarea.setAttribute("readonly", "true")
  textarea.style.position = "fixed"
  textarea.style.left = "-9999px"
  document.body.appendChild(textarea)
  textarea.select()
  try {
    const copied = document.execCommand("copy")
    if (!copied) {
      throw new Error("document.execCommand('copy') returned false")
    }
  } finally {
    document.body.removeChild(textarea)
  }
}

async function writeTextToSystemClipboard(text: string): Promise<void> {
  const clipboard = navigator.clipboard
  if (clipboard?.writeText) {
    try {
      await clipboard.writeText(text)
      return
    } catch (error) {
      console.warn("Clipboard API write failed, trying execCommand", error)
    }
  }
  copyWithExecCommand(text)
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
