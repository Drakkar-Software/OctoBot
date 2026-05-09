// Mirror of implementations/default_rest_exchange.py — the "use it as-is"
// concrete RestExchange. Subclasses extend this when they need to customize
// adapters or auth flow.

import { RestExchange } from "../types/restExchange.js";

export class DefaultRestExchange extends RestExchange {
  static getName(): string {
    return "default";
  }

  static isDefaultExchange(): boolean {
    return true;
  }

  static isSupportingExchange(_name: string): boolean {
    return true;
  }
}
