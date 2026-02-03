## MarketMakingTradingMode

A market making strategy that will maintain the configured order book on the target exchange.

### Behavior
When started, the strategy will create orders according to its configuration. It might cancel open orders when
they are incompatible.

As soon as the maintained order book becomes outdated (from a changed reference price or filled/canceled orders), 
it will be adapted to always try to reflect the configuration.

When a full order book replacement takes place, orders are canceled one by one to avoid leaving an empty book.

The strategy will use all available funds, up to a maximum of what is necessary to cover 
2% of the pair's daily trading volume on the target exchange within the first 3% of the order book depth.

Note: The strategy does not create artificial volume by forcing market orders, it focuses on maintaining an optimized 
order book.

### Configuration
- Bids and asks counts define how many orders should be maintained within the book
- Min spread is the distance (as a % of the current price) between the highest bid and lowest ask
- Max spread is the distance (as a % of the current price) between the lowest bid and highest ask
- Reference exchange is the exchange to get the current price of the traded pair from. It should be a very liquid exchange to avoid arbitrage opportunities.

An advanced version of this market making strategy is available on [OctoBot Market Making](https://market-making.octobot.cloud?utm_source=octobot_mm&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=trading_mode_docs).
