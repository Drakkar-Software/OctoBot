import { describe, expect, it, vi } from "vitest"
import { renderToStaticMarkup } from "react-dom/server"
import type { WalletInfo } from "@/client"

import { WalletRow } from "@/components/Settings/WalletManagement/WalletRow"

vi.mock("@tanstack/react-query", () => ({
  useMutation: () => ({ mutate: vi.fn(), isPending: false, reset: vi.fn() }),
}))

vi.mock("@/components/Settings/WalletManagement/ExportWalletDialog", () => ({
  ExportWalletDialog: () => null,
}))
vi.mock("@/components/Settings/WalletManagement/PairDeviceDialog", () => ({
  PairDeviceDialog: () => null,
}))
vi.mock("@/components/Settings/WalletManagement/RemoveWalletDialog", () => ({
  RemoveWalletDialog: () => null,
}))

const FULL_ADDRESS = "0x1234567890123456789012345678901234567890"

const wallet: WalletInfo = {
  address: FULL_ADDRESS,
  name: "Main",
  is_admin: true,
}

describe("WalletRow login username copy", () => {
  it("renders copy control for the current user wallet", () => {
    const markup = renderToStaticMarkup(
      <WalletRow
        wallet={wallet}
        onRefresh={() => {}}
        currentUserAddress={FULL_ADDRESS}
      />,
    )
    expect(markup).toContain(loginUsernameCopyAriaLabel())
    expect(markup).toContain('data-slot="tooltip-trigger"')
    expect(markup).toContain("lucide-copy")
  })

  it("does not render copy control for another wallet", () => {
    const markup = renderToStaticMarkup(
      <WalletRow
        wallet={wallet}
        onRefresh={() => {}}
        currentUserAddress="0x0000000000000000000000000000000000000001"
      />,
    )
    expect(markup).not.toContain(loginUsernameCopyAriaLabel())
  })
})

function loginUsernameCopyAriaLabel(): string {
  return `Copy login username ${FULL_ADDRESS}`
}