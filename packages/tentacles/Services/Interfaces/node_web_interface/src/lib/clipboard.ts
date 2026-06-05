import { toast } from "sonner"

export function copyTextToClipboard(text: string, description: string): void {
  void navigator.clipboard.writeText(text).then(() => {
    toast.success("Copied to clipboard", { description })
  })
}
