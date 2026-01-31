TradingViewSignalsTradingMode is a trading mode configured to automate orders creation on the 
exchange of your choice by following alerts from 
[TradingView](https://www.tradingview.com/?aff_id=27595) price events, indicators or strategies.

Free TradingView <a target="_blank" rel="noopener" href="https://www.octobot.cloud/en/guides/octobot-interfaces/tradingview/automating-tradingview-free-email-alerts-with-octobot?utm_source=octobot&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=TradingViewSignalsTradingModeDocs">email</a> 
alerts as well as <a target="_blank" rel="noopener" href="https://www.octobot.cloud/en/guides/octobot-interfaces/tradingview/using-a-webhook?utm_source=octobot&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=TradingViewSignalsTradingModeDocs">webhook</a>
alerts can be used to automate trades based on TradingView alerts.

<div class="text-center">
    <div>
    <iframe width="560" height="315" src="https://www.youtube.com/embed/HeOi4PY1ayk" 
    title="TradingView tutorial: automate any strategy with OctoBot custom automation" frameborder="0" allow="accelerometer; autoplay; 
    clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
    </div>
</div>

To know more, checkout the 
<a target="_blank" rel="noopener" href="https://www.octobot.cloud/en/guides/octobot-trading-modes/tradingview-trading-mode?utm_source=octobot&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=TradingViewSignalsTradingModeDocs">
full TradingView trading mode guide</a>.

### Generate your own strategy using AI
Describe your trading strategy to the OctoBot AI strategy generator and get your strategy as Pine Script in seconds.
Automate it with your self-hosted OctoBot or a <a
  href="https://app.octobot.cloud/fr/explore?category=tv&utm_source=octobot&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=tv-trading-mode-tradingview-octobot"
  target="_blank" rel="noopener">
   TradingView OctoBot</a>.
<p>
<a class="btn btn-primary waves-effect" 
  href="https://app.octobot.cloud/creator?utm_source=octobot&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=tv-trading-mode-generate-my-strategy-with-ai"
  target="_blank" rel="noopener">
   Generate my strategy with AI
</a>
</p>

### Alert format cheatsheet
Basic signals have the following format:

```
EXCHANGE=BINANCE
SYMBOL=BTCUSD
SIGNAL=BUY
```

Additional order details can be added to the signal but are optional:

```
ORDER_TYPE=LIMIT
VOLUME=0.01
PRICE=42000
STOP_PRICE=25000
TAKE_PROFIT_PRICE=50000
REDUCE_ONLY=true
```

Where:
- `ORDER_TYPE` is the type of order (LIMIT, MARKET or STOP). Overrides the `Use market orders` parameter
- `VOLUME` is the volume of the order in base asset (BTC for BTC/USDT) it can a flat amount (ex: `0.1` to trade 0.1 BTC on BTC/USD), 
a % of the total portfolio value (ex: `2%`), a % of the available holdings (ex: `12a%`), a % of available holdings associated to the current traded symbol assets (`10s%`) 
or a % of available holdings associated to all configured trading pairs assets (`10t%`). It follows the <a target="_blank" rel="noopener" href="https://www.octobot.cloud/en/guides/octobot-trading-modes/order-amount-syntax?utm_source=octobot&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=TradingViewSignalsTradingModeDocs">
orders amount syntax</a>.
- `PRICE` is the price of the limit order in quote asset (USDT for BTC/USDT). Can also be a delta value from the current price by adding `d` (ex: `10d` or `-0.55d`) or a delta percent from the price (ex: `-5%` or `25.4%`). It follows the <a target="_blank" rel="noopener" href="https://www.octobot.cloud/en/guides/octobot-trading-modes/order-price-syntax?utm_source=octobot&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=TradingViewSignalsTradingModeDocs">
orders price syntax</a>.
- `STOP_PRICE` is the price of the stop order to create. Can also be a delta or % delta like `PRICE`. When increasing the position or buying in spot trading, the stop loss will automatically be created once the initial order is filled. When decreasing the position (or selling in spot) using a LIMIT `ORDER_TYPE`, the stop loss will be created instantly. *Orders crated this way are compatible with PNL history.* It follows the <a target="_blank" rel="noopener" href="https://www.octobot.cloud/en/guides/octobot-trading-modes/order-price-syntax?utm_source=octobot&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=TradingViewSignalsTradingModeDocs">
orders price syntax</a>.
- `TAKE_PROFIT_PRICE` is the price of the take profit order to create. Can also be a delta or % delta like `PRICE`. When increasing the position or buying in spot trading, the take profit will automatically be created once the initial order is filled. When decreasing the position (or selling in spot) using a LIMIT `ORDER_TYPE`, the take profit will be created instantly. *Orders crated this way are compatible with PNL history.* It follows the <a target="_blank" rel="noopener" href="https://www.octobot.cloud/en/guides/octobot-trading-modes/order-price-syntax?utm_source=octobot&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=TradingViewSignalsTradingModeDocs">
orders price syntax</a>. Funds will be evenly split between take profits unless a `TAKE_PROFIT_VOLUME_RATIO` is set for each take profit.  
Multiple take profit prices can be used from `TAKE_PROFIT_PRICE_1`, `TAKE_PROFIT_PRICE_2`, ...
- `TAKE_PROFIT_VOLUME_RATIO` is the ratio of the entry order volume to include in this take profit. Used when multiple 
take profits are set. Specify multiple values using `TAKE_PROFIT_VOLUME_RATIO_1`, `TAKE_PROFIT_VOLUME_RATIO_2`, .... When used, a `TAKE_PROFIT_VOLUME_RATIO` is required for each take profit.  
Exemple: `TAKE_PROFIT_PRICE=1234;TAKE_PROFIT_PRICE_1=1456;TAKE_PROFIT_VOLUME_RATIO_1=1;TAKE_PROFIT_VOLUME_RATIO_2=2` will split 33% of entry amount in TP 1 and 67% in TP 2.
- `REDUCE_ONLY` when true, only reduce the current position (avoid accidental short position opening when reducing a long position). **Only used in futures trading**. Default is false
- `TAG` is an identifier to give to the orders to create.
- `LEVERAGE` the leverage value to use when trading futures.

When not specified, orders volume and price are automatically computed based on the current 
asset price and holdings.

Orders can be cancelled using the following format:
``` bash
EXCHANGE=binance
SYMBOL=ETHBTC
SIGNAL=CANCEL
```

Additional cancel parameters:
- `PARAM_SIDE` is the side of the orders to cancel, it can be `buy` or `sell` to only cancel buy or sell orders.
- `TAG` is the tag of the order(s) to cancel. It can be used to only cancel orders that have been created with a specific tag.

Note: `;` can also be used to separate signal parameters, exemple: `EXCHANGE=binance;SYMBOL=ETHBTC;SIGNAL=CANCEL` is equivalent to the previous example.

Find the full TradingView alerts format on
<a target="_blank" rel="noopener" href="https://www.octobot.cloud/en/guides/octobot-interfaces/tradingview/alert-format?utm_source=octobot&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=TradingViewSignalsTradingModeDocs">
the TradingView alerts format guide</a>.

