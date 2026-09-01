import { describe, expect, it } from "vitest"

import type { Account, ExchangeConfig, Strategy } from "@/client"
import {
  buildAccountEditUserActionJson,
  buildAutomationCreateUserActionJsonForAccount,
  buildAutomationCreateUserActionJsonForStrategy,
  buildAutomationRestartUserActionJson,
  buildAutomationSignalUserActionJson,
  buildAutomationStopUserActionJson,
  buildResetAccountTradingDataUserActionJson,
  buildExchangeConfigEditUserActionJson,
  buildStrategyEditUserActionJson,
  buildUpdateHistoricalExchangesDataUserActionJson,
  buildUserActionTemplate,
  buildUserActionTemplateJson,
  defaultSignalPayloadText,
  TEMPLATE_ACCOUNT_ID,
  TEMPLATE_AUTOMATION_ID,
  TEMPLATE_MASTER_STRATEGY_ID,
  userActionTemplateKeyFromActionType,
} from "@/lib/debug/user-action-templates"

const CANONICAL_UUID_V4_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/

describe("defaultSignalPayloadText", () => {
  it("returns sample payloads for payload signal types", () => {
    expect(defaultSignalPayloadText("actions")).toContain("dsl_script")
    expect(defaultSignalPayloadText("trading_signal")).toContain("strategy_id")
    expect(defaultSignalPayloadText("forced_trigger")).toBe("")
  })
})

describe("buildUserActionTemplate", () => {
  it("builds an automation stop template with a unique user-action id", () => {
    const firstAction = buildUserActionTemplate("automation_stop")
    const secondAction = buildUserActionTemplate("automation_stop")
    expect(firstAction.id).toMatch(
      /^ua-manual-automation_stop-[0-9a-f-]{36}$/,
    )
    expect(secondAction.id).not.toBe(firstAction.id)
    const action = firstAction
    expect(action.configuration).toMatchObject({
      action_type: "automation_stop",
      id: TEMPLATE_AUTOMATION_ID,
      cancel_orders: false,
    })
  })

  it("builds an automation restart template", () => {
    const action = buildUserActionTemplate("automation_restart")
    expect(action.id).toContain("automation_restart")
    expect(action.configuration).toMatchObject({
      action_type: "automation_restart",
      id: TEMPLATE_AUTOMATION_ID,
    })
  })

  it("builds an automation create template with a random configuration id", () => {
    const action = buildUserActionTemplate("automation_create")
    expect(action.configuration).toMatchObject({
      action_type: "automation_create",
    })

    const automationConfiguration = (
      action.configuration as { configuration: Record<string, unknown> }
    ).configuration
    const automationId = automationConfiguration.id
    expect(typeof automationId).toBe("string")
    const automationIdString = automationId as string
    expect(automationIdString).toMatch(CANONICAL_UUID_V4_PATTERN)
    expect(automationIdString).toBe(automationIdString.toLowerCase())
  })

  it("builds an automation edit template without configuration id", () => {
    const action = buildUserActionTemplate("automation_edit")
    expect(action.configuration).toMatchObject({
      action_type: "automation_edit",
      id: TEMPLATE_AUTOMATION_ID,
    })

    const automationConfiguration = (
      action.configuration as { configuration: Record<string, unknown> }
    ).configuration
    expect(automationConfiguration).not.toHaveProperty("id")
  })

  it("builds an account create template with default USDC assets", () => {
    const action = buildUserActionTemplate("account_create")
    expect(action.configuration).toMatchObject({
      action_type: "account_create",
    })

    const accountConfiguration = (
      action.configuration as { configuration: Record<string, unknown> }
    ).configuration
    expect(accountConfiguration.assets).toEqual([
      {
        trading_type: "spot",
        assets: [{ symbol: "USDC", total: 1000, available: 1000 }],
      },
    ])
  })

  it("builds an account edit template without assets", () => {
    const action = buildUserActionTemplate("account_edit")
    expect(action.configuration).toMatchObject({
      action_type: "account_edit",
      id: TEMPLATE_ACCOUNT_ID,
    })

    const accountConfiguration = (
      action.configuration as { configuration: Record<string, unknown> }
    ).configuration
    expect(accountConfiguration).not.toHaveProperty("assets")
  })

  it("builds a grid strategy create template", () => {
    const action = buildUserActionTemplate("strategy_create_grid")
    expect(action.configuration).toMatchObject({
      action_type: "strategy_create",
    })

    const strategy = (
      action.configuration as { configuration: Record<string, unknown> }
    ).configuration
    const tradingConfiguration = strategy.configuration as Record<
      string,
      unknown
    >
    expect(tradingConfiguration.configuration_type).toBe("trading_tentacles")
    expect(tradingConfiguration.name).toBe("GridTradingMode")

    const config = tradingConfiguration.config as Record<string, unknown>
    const pairSettings = config.pair_settings as Array<Record<string, unknown>>
    expect(pairSettings[0].pair).toBe("BTC/USDC")
    expect(tradingConfiguration).not.toHaveProperty("symbols")
  })

  it("builds an index strategy create template", () => {
    const action = buildUserActionTemplate("strategy_create_index")
    expect(action.configuration).toMatchObject({
      action_type: "strategy_create",
    })

    const strategy = (
      action.configuration as { configuration: Record<string, unknown> }
    ).configuration
    const tradingConfiguration = strategy.configuration as Record<
      string,
      unknown
    >
    expect(tradingConfiguration.configuration_type).toBe("trading_tentacles")
    expect(tradingConfiguration.name).toBe("IndexTradingMode")

    const config = tradingConfiguration.config as Record<string, unknown>
    expect(config.index_content).toEqual([{ name: "BTC", value: 1.0 }])
    expect(config.rebalance_trigger_min_percent).toBe(5.0)
  })

  it("builds a copy strategy create template", () => {
    const action = buildUserActionTemplate("strategy_create_copy")
    expect(action.configuration).toMatchObject({
      action_type: "strategy_create",
    })

    const strategy = (
      action.configuration as { configuration: Record<string, unknown> }
    ).configuration
    expect(strategy.reference_market).toBe("USDC")

    const copyConfiguration = strategy.configuration as Record<string, unknown>
    expect(copyConfiguration.configuration_type).toBe("copy")
    expect(copyConfiguration.strategy_id).toBe(TEMPLATE_MASTER_STRATEGY_ID)
  })

  it("builds a DCA strategy create template with two evaluators", () => {
    const action = buildUserActionTemplate("strategy_create_dca")
    expect(action.id).toBe("ua-manual-strategy_create_dca")
    expect(action.configuration).toMatchObject({
      action_type: "strategy_create",
    })

    const strategy = (
      action.configuration as { configuration: Record<string, unknown> }
    ).configuration
    expect(strategy.reference_market).toBe("USDC")

    const tradingConfiguration = strategy.configuration as Record<
      string,
      unknown
    >
    expect(tradingConfiguration.configuration_type).toBe("trading_tentacles")
    expect(tradingConfiguration.name).toBe("DCATradingMode")
    expect(tradingConfiguration).not.toHaveProperty("symbols")

    const dcaConfig = tradingConfiguration.config as Record<string, unknown>
    expect(dcaConfig.trigger_mode).toBe("Maximum evaluators signals based")
    expect(dcaConfig.use_init_entry_orders).toBe(false)
    expect(dcaConfig.use_stop_losses).toBe(false)
    expect(dcaConfig.stop_loss_price_percent).toBe(10)
    expect(dcaConfig.trading_pairs).toEqual([])

    const evaluators = tradingConfiguration.evaluators as Array<{
      name: string
      config: Record<string, unknown>
      symbols: string[]
    }>
    expect(evaluators).toHaveLength(2)
    expect(evaluators[0].name).toBe("RSIMomentumEvaluator")
    expect(evaluators[1].name).toBe("EMAMomentumEvaluator")
    expect(evaluators[0].symbols).toEqual(["BTC/USDC", "ETH/USDC"])

    const strategies = tradingConfiguration.strategies as Array<{
      name: string
      config: Record<string, unknown>
      time_frames: string[]
    }>
    expect(strategies).toHaveLength(1)
    expect(strategies[0].time_frames).toEqual(["1h"])
    expect(strategies[0].name).toBe("SimpleStrategyEvaluator")
  })

  it("builds a DCA always-long strategy create template", () => {
    const action = buildUserActionTemplate("strategy_create_dca_always_long")
    expect(action.id).toBe("ua-manual-strategy_create_dca_always_long")

    const strategy = (
      action.configuration as { configuration: Record<string, unknown> }
    ).configuration
    const tradingConfiguration = strategy.configuration as Record<
      string,
      unknown
    >
    expect(tradingConfiguration.name).toBe("DCATradingMode")
    expect(tradingConfiguration).not.toHaveProperty("symbols")
    expect(tradingConfiguration).not.toHaveProperty("evaluators")
    expect(tradingConfiguration).not.toHaveProperty("strategies")

    const dcaConfig = tradingConfiguration.config as Record<string, unknown>
    expect(dcaConfig.trigger_mode).toBe("Always trigger long")
    expect(dcaConfig.use_init_entry_orders).toBe(true)
    expect(dcaConfig.trading_pairs).toEqual(["BTC/USDC", "ETH/USDC"])
    expect(dcaConfig.time_frames).toEqual(["1h"])
  })

  it("builds a DCA time-based daily strategy create template", () => {
    const action = buildUserActionTemplate("strategy_create_dca_time_based")
    expect(action.id).toBe("ua-manual-strategy_create_dca_time_based")

    const strategy = (
      action.configuration as { configuration: Record<string, unknown> }
    ).configuration
    const tradingConfiguration = strategy.configuration as Record<
      string,
      unknown
    >
    expect(tradingConfiguration.name).toBe("DCATradingMode")
    expect(tradingConfiguration).not.toHaveProperty("evaluators")
    expect(tradingConfiguration).not.toHaveProperty("strategies")

    const dcaConfig = tradingConfiguration.config as Record<string, unknown>
    expect(dcaConfig.trigger_mode).toBe("Time based")
    expect(dcaConfig.minutes_before_next_buy).toBe(1440)
    expect(dcaConfig.trading_pairs).toEqual(["BTC/USDC", "ETH/USDC"])
    expect(dcaConfig.use_init_entry_orders).toBe(false)
    expect(dcaConfig.time_frames).toEqual([])
  })

  it("builds a market making strategy create template", () => {
    const action = buildUserActionTemplate("strategy_create_market_making")
    expect(action.id).toBe("ua-manual-strategy_create_market_making")

    const strategy = (
      action.configuration as { configuration: Record<string, unknown> }
    ).configuration
    expect(strategy.reference_market).toBe("USDC")

    const marketMakingConfiguration = strategy.configuration as Record<
      string,
      unknown
    >
    expect(marketMakingConfiguration.configuration_type).toBe("market_making")

    const pairSettings = marketMakingConfiguration.pair_settings as Array<
      Record<string, unknown>
    >
    expect(pairSettings).toHaveLength(1)
    expect(pairSettings[0].trading_pair).toBe("BTC/USDC")
    expect(pairSettings[0].exchange).toBe("binance")
    expect(pairSettings[0].min_spread).toBe(5)
    expect(pairSettings[0].max_spread).toBe(20)
  })

  it("builds a generic process OctoBot strategy create template", () => {
    const action = buildUserActionTemplate("strategy_create_generic_process")
    expect(action.id).toBe("ua-manual-strategy_create_generic_process")
    expect(action.configuration).toMatchObject({
      action_type: "strategy_create",
    })

    const strategy = (
      action.configuration as { configuration: Record<string, unknown> }
    ).configuration
    expect(strategy.reference_market).toBe("USDC")
    expect(strategy.id).toMatch(CANONICAL_UUID_V4_PATTERN)

    const genericProcessConfiguration = strategy.configuration as Record<
      string,
      unknown
    >
    expect(genericProcessConfiguration.configuration_type).toBe("generic_process")
    expect(genericProcessConfiguration).not.toHaveProperty("profile_data")
  })

  it("builds an update historical exchanges data template", () => {
    const action = buildUserActionTemplate("update_historical_exchanges_data")
    expect(action.id).toContain("update_historical_exchanges_data")
    expect(action.configuration).toMatchObject({
      action_type: "update_historical_exchanges_data",
    })
  })

  it("builds a reset account trading data template", () => {
    const action = buildUserActionTemplate("reset_account_trading_data")
    expect(action.id).toContain("reset_account_trading_data")
    expect(action.configuration).toMatchObject({
      action_type: "reset_account_trading_data",
      account_ids: [TEMPLATE_ACCOUNT_ID],
    })
  })
})

describe("buildUserActionTemplateJson", () => {
  it("returns pretty-printed JSON", () => {
    const json = buildUserActionTemplateJson("automation_stop")
    expect(JSON.parse(json).configuration.action_type).toBe("automation_stop")
  })
})

describe("userActionTemplateKeyFromActionType", () => {
  it("returns the action type unchanged", () => {
    expect(userActionTemplateKeyFromActionType("account_edit")).toBe(
      "account_edit",
    )
  })
})

describe("buildAccountEditUserActionJson", () => {
  it("embeds the account configuration", () => {
    const account: Account = {
      id: "acc-1",
      name: "Main",
      is_simulated: true,
      created_at: "2024-01-01T00:00:00.000Z",
    }
    const json = JSON.parse(buildAccountEditUserActionJson(account))
    expect(json.configuration.id).toBe("acc-1")
    expect(json.configuration.configuration).toEqual(account)
  })
})

describe("buildUpdateHistoricalExchangesDataUserActionJson", () => {
  it("includes the account id in account_ids", () => {
    const json = JSON.parse(
      buildUpdateHistoricalExchangesDataUserActionJson("acc-history-1"),
    )
    expect(json.configuration).toMatchObject({
      action_type: "update_historical_exchanges_data",
      account_ids: ["acc-history-1"],
    })
  })
})

describe("buildResetAccountTradingDataUserActionJson", () => {
  it("includes the account id in account_ids", () => {
    const json = JSON.parse(
      buildResetAccountTradingDataUserActionJson("acc-reset-1"),
    )
    expect(json.configuration).toMatchObject({
      action_type: "reset_account_trading_data",
      account_ids: ["acc-reset-1"],
    })
  })
})

describe("buildExchangeConfigEditUserActionJson", () => {
  it("embeds the exchange config", () => {
    const config: ExchangeConfig = {
      id: "cfg-1",
      name: "Binance",
      exchange: "binance",
      sandboxed: false,
    }
    const json = JSON.parse(buildExchangeConfigEditUserActionJson(config))
    expect(json.configuration.id).toBe("cfg-1")
  })

  it("preserves historical_trade_symbols when present", () => {
    const config: ExchangeConfig = {
      id: "cfg-1",
      name: "Kraken",
      exchange: "kraken",
      sandboxed: false,
      historical_trade_symbols: ["BTC/USDT", "ADA/USDT"],
    }
    const json = JSON.parse(buildExchangeConfigEditUserActionJson(config))
    expect(json.configuration.configuration.historical_trade_symbols).toEqual([
      "BTC/USDT",
      "ADA/USDT",
    ])
  })
})

describe("buildStrategyEditUserActionJson", () => {
  it("embeds the strategy configuration", () => {
    const strategy: Strategy = {
      id: "strat-1",
      version: "1.0.0",
      name: "Alpha",
      reference_market: "USDT",
      configuration: {
        configuration_type: "generic_process",
        profile_data: {},
      },
    } as Strategy
    const json = JSON.parse(buildStrategyEditUserActionJson(strategy))
    expect(json.configuration.id).toBe("strat-1")
  })
})

describe("buildAutomationStopUserActionJson", () => {
  it("targets the automation id with a unique user-action id", () => {
    const firstJson = JSON.parse(buildAutomationStopUserActionJson("auto-1"))
    const secondJson = JSON.parse(buildAutomationStopUserActionJson("auto-1"))
    expect(firstJson.id).toMatch(/^ua-stop-auto-1-[0-9a-f-]{36}$/)
    expect(secondJson.id).not.toBe(firstJson.id)
    expect(firstJson.configuration).toEqual({
      action_type: "automation_stop",
      id: "auto-1",
      cancel_orders: false,
    })
  })
})

describe("buildAutomationRestartUserActionJson", () => {
  it("targets the automation id", () => {
    const json = JSON.parse(buildAutomationRestartUserActionJson("auto-1"))
    expect(json.configuration).toEqual({
      action_type: "automation_restart",
      id: "auto-1",
    })
  })
})

describe("buildAutomationSignalUserActionJson", () => {
  it("includes the selected signal type", () => {
    const json = JSON.parse(
      buildAutomationSignalUserActionJson("auto-1", "actions"),
    )
    expect(json.configuration.signal_type).toBe("actions")
  })
})

describe("buildAutomationCreateUserActionJsonForAccount", () => {
  it("binds the account reference", () => {
    const account: Account = {
      id: "acc-1",
      name: "Main",
      is_simulated: true,
      created_at: "2024-01-01T00:00:00.000Z",
    }
    const json = JSON.parse(
      buildAutomationCreateUserActionJsonForAccount(account),
    )
    expect(json.configuration.configuration.accounts).toEqual([{ id: "acc-1" }])
    expect(json.configuration.configuration.id).toMatch(
      CANONICAL_UUID_V4_PATTERN,
    )
  })
})

describe("buildAutomationCreateUserActionJsonForStrategy", () => {
  it("binds the strategy reference", () => {
    const strategy: Strategy = {
      id: "strat-1",
      version: "2.0.0",
      name: "Grid",
      reference_market: "USDT",
      configuration: {
        configuration_type: "trading_tentacles",
        name: "GridTradingMode",
        config: { pair_settings: [] },
      },
    } as Strategy
    const json = JSON.parse(
      buildAutomationCreateUserActionJsonForStrategy(strategy),
    )
    expect(json.configuration.configuration.strategy).toEqual({
      id: "strat-1",
      version: "2.0.0",
      emit_signals: false,
    })
    expect(json.configuration.configuration.id).toMatch(
      CANONICAL_UUID_V4_PATTERN,
    )
  })
})
