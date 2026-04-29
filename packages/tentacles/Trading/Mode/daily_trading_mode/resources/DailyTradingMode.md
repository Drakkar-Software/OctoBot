The DailyTradingMode will consider every compatible strategy and evaluator and average their evaluation to create
each update.

It will create orders when its state changes to 
a state that is different from the previous one and that is not NEUTRAL.

A LONG state will trigger a buy order. A SHORT state will trigger a sell order. 

<div class="text-center">
    <iframe width="560" height="315" src="https://www.youtube.com/embed/e-GqmTfrchY?showinfo=0&amp;rel=0" 
    title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; 
    clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
</div>

To know more, checkout the 
<a target="_blank" rel="noopener" href="https://www.octobot.cloud/en/guides/octobot-trading-modes/daily-trading-mode?utm_source=octobot&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=DailyTradingModeDocs">
full Daily trading mode guide</a>.

### Default mode
On Default mode, the DailyTradingMode will cancel previously created open orders 
and create new ones according to its new state. 
In this mode, both buy and sell orders will be exclusively created upon strategy and evaluator signals.

### Target profits mode
On Target profits mode, the DailyTradingMode will only listen for LONG signals when trading spot 
and position-increasing signals when trading futures, which means both SHORT and LONG. When such a signal is received, it will create an entry order 
that will be followed by a take profit (and possibly a stop-loss) when filled. In this mode, only entry signals are 
defined by your strategy and evaluator configuration as take profit and stop loss targets are defined in 
the Target profits mode configuration.  
*Using the DailyTradingMode in Target profits mode is compatible with PNL history.*

### About futures trading  
The **Target profits** mode is more adapted to futures trading as it creates take profits and stop losses (when enabled) 
to close created positions.
