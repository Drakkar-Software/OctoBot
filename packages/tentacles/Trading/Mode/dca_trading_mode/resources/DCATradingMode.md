Dollar cost averaging (DCA) is a trading mode that can help you lower the amount you pay for investments and 
minimize risk. Instead of purchasing investments at a single price point, with dollar cost averaging you buy 
in smaller amounts at regular intervals.

<div class="text-center">
    <div>
    <iframe width="560" height="315" src="https://www.youtube.com/embed/519pwSV1uwE?si=MT9e1Gqp9WWw45Z" 
    title="Build your own Smart DCA strategy" frameborder="0" allow="accelerometer; autoplay; 
    clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
    </div>
</div>

OctoBot's DCA is more than just a simple regular DCA technique, it allows you to accurately automate your 
entries and exit conditions in a simple, yet very powerful way.

To know more, checkout the 
<a target="_blank" rel="noopener" href="https://www.octobot.cloud/en/guides/octobot-trading-modes/dca-trading-mode?utm_source=octobot&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=DCATradingModeDocs">
full DCA trading mode guide</a>.

### In a nutshell
- Entries can be triggered either:
    - On a pure time base, regardless of price.
    - Upon enabled evaluators maximum signals (only 1 or -1 evaluations). In this case, the latest evaluation will 
        prevail when using limit entry orders: previous evaluations open orders will be cancelled.
- Entries can be market or limit orders.
- Once an entry is filled, you can choose to exit/sell the assets yourself (manually) or automatically 
create a take profit at your price target. 
- You can enable stop losses protect your holdings once an entry is filled.
- It is also possible to split entries and exits into multiple orders at regular price intervals to profit even more 
from the dollar cost averaging effect.

Over the long term, dollar cost averaging can help lower your investment costs and boost your returns by optimizing 
entry and exit prices according to your goals.

_Note: When using default configuration, DCA Trading mode will buy 50$ (or unit of the quote currency: USDT for BTC/USDT) 
each week._


_This trading mode supports PNL history when take profit exit orders are enabled._
