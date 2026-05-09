// Mirror of implementations/default_websocket_exchange.py.

import { WebSocketExchange } from "../types/websocketExchange.js";

export class DefaultWebSocketExchange extends WebSocketExchange {
  static getName(): string {
    return "default";
  }

  static isDefaultExchange(): boolean {
    return true;
  }
}
