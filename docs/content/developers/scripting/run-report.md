---
title: "Run report"
description: "Learn how to create, display and find your strategy run report at the end of each OctoBot script strategy execution."
sidebar_position: 9
---

# Run report

Each full execution of your strategy can generate a complete report.

To generate a report at the end of a strategy run, add the following instruction

```python
await res.plot(show=True)
```

> Tip: Use the `show` parameter to automatically open the report on your web browser

![octobot pro report btc usdt with chart trades portfolio value and rsi](/images/guides/octobot-pro/octobot-pro-report-btc-usdt-with-chart-trades-portfolio-value-and-rsi.jpg)

By default, each run report is stored in its run directory, in 
`user/data/BacktesterTradingMode/default_campaign/backtesting/backtesting_X/report.html`. 
Where X is the identifier of your backtesting run.

> This report can be customized to include any information that would be useful to you. 
Do customize your report, checkout the following articles.
