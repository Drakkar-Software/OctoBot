export const DEVICE_DATABASE_NAME = "octobot_device"

export const RESET_CONFIRM_MESSAGE =
  "This will clear all local data for OctoBot Node on this device, including " +
  "sign-in session, wallet keys, templates, and UI cache. You will need to " +
  "sign in again. Continue?"

export const RECOVERY_EXPLANATION =
  "This browser saved your wallet address but not your passphrase (or it could " +
  "not be read). That is not the same as a wrong passphrase on the node. " +
  'Resetting clears local app data on this device; you will return to the sign-in ' +
  "screen and can unlock again with your wallet passphrase."

export const INSECURE_CONTEXT_HEADING = "Secure context required"

export const INSECURE_CONTEXT_WHY_LEAD =
  "OctoBot sends and stores sensitive information (accounts, keys). Your browser " +
  "only allows that on a safe connection: HTTPS, or opening the app at 127.0.0.1 " +
  "or localhost on the computer where the node runs."

export const INSECURE_CONTEXT_WHY_ADDRESS_BEFORE =
  "The address in your address bar right now ("

export const INSECURE_CONTEXT_WHY_ADDRESS_AFTER = ") is not one of those."

export const INSECURE_CONTEXT_SAME_COMPUTER_LEAD =
  "If the node process runs on this computer, open this address in your browser:"

export const INSECURE_CONTEXT_OPTION_LOCAL_TITLE = "Option 1: On this computer (local)"

export const INSECURE_CONTEXT_OPTION_LOCAL_SUBLABEL =
  "Use this if the node runs on the machine you’re using now."

export const INSECURE_CONTEXT_OPTION_REMOTE_TITLE =
  "Option 2: From another device (remote)"

export const MAGIC_DNS_TRAILING_INVALID =
  "Remove the trailing dot or symbol at the end of the hostname."

export const FEEDBACK_EMPTY_JOURNAL_HINT =
  "No diagnostic events are attached yet. You can still send feedback using the note below."


export const INSECURE_CONTEXT_REMOTE_LEAD =
  "From another computer or server, use HTTPS. The simplest way is Tailscale: a " +
  "private network that also works with the OctoBot mobile app. Use the button " +
  "below for setup steps."

export const TAILSCALE_REMOTE_ACCESS_BUTTON_LABEL = "Set up remote access"

export const TAILSCALE_REMOTE_ACCESS_DIALOG_TITLE = "Remote access with Tailscale"

export const TAILSCALE_ADMIN_CONSOLE_MACHINES_URL =
  "https://console.tailscale.com/admin/machines"

export const TAILSCALE_FULL_DOMAIN_EXAMPLE = "my-pc.tail12345.ts.net"

export const TAILSCALE_AVOID_IP_HTTPS_WARNING =
  'If you see "ERR_SSL_PROTOCOL_ERROR", remember to run the step 2 command on the node\'s computer.'

export const TAILSCALE_SERVE_NOT_ENABLED_ON_TAILNET_MESSAGE =
  "Serve is not enabled on your tailnet"

export const TAILSCALE_SERVE_STARTED_RUNNING_MESSAGE = "Serve started and running"

export const TAILSCALE_MAGICDNS_REACHABILITY_LEAD =
  "Your OctoBot node is securely reachable from this MagicDNS name, by any other " +
  "device connected to your Tailscale network."

export const MAGIC_DNS_OPEN_IN_BROWSER_LABEL = "🔗 Open in browser"

export const MAGIC_DNS_INPUT_LABEL = "Full domain (from Tailscale admin)"

export const MAGIC_DNS_INPUT_PLACEHOLDER = "my-node.my-tailnet.ts.net"

export const MAGIC_DNS_ENTER_NAME = "Enter your machine’s MagicDNS name."

export const MAGIC_DNS_REMOVE_SPACES =
  "Remove spaces — use only the hostname (example: my-pc.my-tailnet.ts.net)."

export const MAGIC_DNS_INVALID_SHAPE =
  "That doesn’t look like a MagicDNS name — it usually looks like my-machine.my-tailnet.ts.net."

export const MAGIC_DNS_BAD_CHARACTERS =
  "Use only letters, numbers, dots, and hyphens."

export const MAGIC_DNS_REMOTE_URL_LABEL = "Open your node at:"
