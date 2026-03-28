---
title: "Rapport d'exécution"
description: "Apprenez comment créer, afficher et trouver le rapport d'exécution de votre stratégie à la fin de chaque exécution de stratégie avec OctoBot Script."
sidebar_position: 9
---



# Rapport d'exécution

:::info
  La traduction française de cette page est en cours.
:::

Each full execution of your strategy can generate a complete report.

To generate a report at the end of a strategy run, add the following instruction

```python
await res.plot(show=True)
```

> Tip: Use the `show` parameter to automatically open the report on your web browser

![rapport octobot pro avec btc usdt avec graphiques de trades et portfolio et rsi](/images/guides/octobot-pro/octobot-pro-report-btc-usdt-with-chart-trades-portfolio-value-and-rsi.jpg)

By default, each run report is stored in its run directory, in 
`user/data/BacktesterTradingMode/default_campaign/backtesting/backtesting_X/report.html`. 
Where X is the identifier of your backtesting run.

> This report can be customized to include any information that would be useful to you. 
Do customize your report, checkout the following articles.
