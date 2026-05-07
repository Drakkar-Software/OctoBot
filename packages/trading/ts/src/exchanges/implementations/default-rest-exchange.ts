// Default exchange with no overrides — uses pure CCXTAdapter
import type { ExchangeConfig } from "../../types/index.js"
import { RestExchange } from "../types/rest-exchange.js"

export class DefaultRestExchange extends RestExchange {
  static override getName(): string {
    return "default"
  }

  constructor(config: ExchangeConfig) {
    super(config)
  }
}
