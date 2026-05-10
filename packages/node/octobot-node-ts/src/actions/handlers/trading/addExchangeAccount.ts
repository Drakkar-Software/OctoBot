import type { Action, AddExchangeAccountAction, AutomationsState } from "@drakkarsoftware/octobot-protocol";
import { AccountType } from "@drakkarsoftware/octobot-protocol";
import type { ExchangeManager } from "@drakkarsoftware/octobot-trading";
import { ExchangeBuilder } from "@drakkarsoftware/octobot-trading";
import { InvalidAccountError } from "../../../errors.js";
import type { AutomationContext } from "../../../runner.js";

export function createAddExchangeAccountHandler(registry: Map<string, ExchangeManager>) {
  return async function addExchangeAccountHandler(
    action: Action,
    ctx: AutomationContext,
    _state: AutomationsState,
  ): Promise<unknown> {
    const { account } = action as AddExchangeAccountAction;

    if (account.accountType !== AccountType.Exchange) {
      throw new InvalidAccountError(`Expected Exchange account, got ${account.accountType}`);
    }
    if (!account.exchangeAccount?.exchange) {
      throw new InvalidAccountError("Exchange account must have an exchange name");
    }
    if (!account.isSimulated && !account.exchangeAccount.apiKey) {
      throw new InvalidAccountError("Live exchange account must have an apiKey");
    }

    if (!account.isSimulated) {
      const existing = registry.get(account.id);
      if (existing) await existing.stop();

      const { exchange, apiKey, apiSecret, apiPassphrase } = account.exchangeAccount;
      const manager = new ExchangeBuilder(exchange)
        .setCredentials({ apiKey, secret: apiSecret, password: apiPassphrase })
        .build();
      registry.set(account.id, manager);
    }

    ctx.replaceAccount?.(account);
    return account;
  };
}
