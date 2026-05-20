---
title: "Tracer des indicateurs"
description: "Apprenez comment représenter graphiquement des indicateurs techniques tels que le RSI ou l'EMA dans votre rapport d'exécution de stratégie en utilisant Python à l'aide d'OctoBot Script."
sidebar_position: 10
---



# Tracer des indicateurs

:::info
  La traduction française de cette page est en cours.
:::

Indicators and associated signals can be easily plotted using the 
`plot_indicator(ctx, name, x, y, signals)` keyword.

Where:
- `name`: name of the indicator on the chart 
- `x`: values to use for the x axis
- `y`: values to use for the y axis
- `signal`: (optional) x values for which a signal is fired

Example where the goal is to plot the value of the rsi indicator from 
the [example script](/guides/octobot-script#script).
``` python
await obs.plot_indicator(ctx, "RSI", time_values, indicator_values, signal_times)
```
