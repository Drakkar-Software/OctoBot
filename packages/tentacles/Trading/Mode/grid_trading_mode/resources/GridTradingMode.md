Places a fixed amount of buy and sell orders at fixed intervals to profit from any market move. When an order is filled,
a mirror order is instantly created and generates profit when completed.

To know more, checkout the 
<a target="_blank" rel="noopener" href="https://www.octobot.cloud/en/guides/octobot-trading-modes/grid-trading-mode?utm_source=octobot&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=GridTradingModeDocs">
full Grid trading mode guide</a>.

#### Default configuration
When left unspecified for a trading pair, the grid will be initialized with a spread
of 1.5% of the current price and an increment of 0.5% and a maximum of 20 buy and sell orders.

When enough funds are available, the default configuration will result in:
- Up to 20 buy order covering 99.25% to 89.5% of the current price
- Up to 20 sell orders covering 100.75% to 110.5% of the current price 

#### Trading pair configuration
You can customize the grid for each trading pair. To configure a pair, enter:
- The name of the pair 
- The interval between buy and sell (spread) 
- The interval between each order (increment)
- The amount of initial buy and sell orders to create 

#### Trailing options
A grid can only operate within its price range. However, when trailing options are enabled, 
the whole grid can be automatically cancelled and recreated 
when the traded asset's price moves beyond the grid range. In this case, a market order can be executed in order to 
have the necessary funds to create the grid buy and sell orders.

#### Profits
Profits will be made from price movements within the covered price area.  
It never "sells at a loss", but always at a profit, therefore OctoBot never cancels any orders when using the Grid Trading Mode.

To apply changes to the Grid Trading Mode settings, you will have to manually cancel orders and restart your OctoBot.  
This trading mode instantly places opposite side orders when an order is filled.

This trading mode has been made possible thanks to the support of PKBO & Calusari.

_This trading mode supports PNL history._
