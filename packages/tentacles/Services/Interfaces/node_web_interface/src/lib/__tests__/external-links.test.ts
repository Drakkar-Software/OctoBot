import { describe, expect, it } from "vitest"

import {
  OCTOBOT_CONNECT_GUIDE_COMMON_ISSUES_URL,
  OCTOBOT_CONNECT_GUIDE_SAME_COMPUTER_WEB_URL,
  OCTOBOT_CONNECT_GUIDE_TWO_INTERFACES_URL,
  OCTOBOT_CONNECT_GUIDE_URL,
  OCTOBOT_TAILSCALE_CONNECT_GUIDE_URL,
} from "../external-links"

describe("external-links connect guide anchors", () => {
  it("uses expected node-connect-guide paths and hashes", () => {
    expect(OCTOBOT_CONNECT_GUIDE_URL).toBe(
      "https://www.octobot.cloud/en/guides/octobot-installation/node-connect-guide",
    )
    expect(OCTOBOT_CONNECT_GUIDE_SAME_COMPUTER_WEB_URL).toBe(
      `${OCTOBOT_CONNECT_GUIDE_URL}#local-network`,
    )
    expect(OCTOBOT_TAILSCALE_CONNECT_GUIDE_URL).toBe(
      `${OCTOBOT_CONNECT_GUIDE_URL}#private-network`,
    )
    expect(OCTOBOT_CONNECT_GUIDE_COMMON_ISSUES_URL).toBe(
      `${OCTOBOT_CONNECT_GUIDE_URL}#common-issues`,
    )
    expect(OCTOBOT_CONNECT_GUIDE_TWO_INTERFACES_URL).toBe(
      `${OCTOBOT_CONNECT_GUIDE_URL}#the-two-interfaces-you-will-use`,
    )
  })
})
