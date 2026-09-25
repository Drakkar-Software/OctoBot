import { describe, expect, it } from "vitest"
import { renderToStaticMarkup } from "react-dom/server"

import { RecoverWalletIdentityHeader } from "@/routes/login/-RecoverWalletIdentityHeader"

const SAMPLE_ADDRESS = "0x1234567890abcdef1234567890abcdef12345678"

describe("RecoverWalletIdentityHeader", () => {
  it("shows_name_before_address_when_name_provided", () => {
    const markup = renderToStaticMarkup(
      <RecoverWalletIdentityHeader
        address={SAMPLE_ADDRESS}
        walletName="Alice"
      />,
    )
    expect(markup).toContain('data-testid="recover-wallet-name"')
    expect(markup).toContain('data-testid="recover-wallet-address"')
    const aliceIndex = markup.indexOf("Alice")
    const addressIndex = markup.indexOf("0x1234")
    expect(aliceIndex).toBeGreaterThan(-1)
    expect(addressIndex).toBeGreaterThan(-1)
    expect(aliceIndex).toBeLessThan(addressIndex)
  })

  it("shows_no_name_placeholder_when_name_missing", () => {
    const markup = renderToStaticMarkup(
      <RecoverWalletIdentityHeader
        address={SAMPLE_ADDRESS}
        walletName={null}
        walletNamePending={false}
      />,
    )
    expect(markup).toContain("No name")
    expect(markup).toContain('data-testid="recover-wallet-address"')
  })

  it("reserves_name_line_while_pending", () => {
    const markup = renderToStaticMarkup(
      <RecoverWalletIdentityHeader
        address={SAMPLE_ADDRESS}
        walletNamePending={true}
      />,
    )
    expect(markup).toContain('data-testid="recover-wallet-name"')
    expect(markup).toContain('data-wallet-name-pending="true"')
    expect(markup).toContain('aria-busy="true"')
    expect(markup).not.toContain("No name")
  })
})
