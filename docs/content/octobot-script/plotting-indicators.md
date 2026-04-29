---
title: "Plotting indicators"
description: "Learn how to plot technical indicators such as RSI or EMA on your strategy run report with python using OctoBot script."
sidebar_position: 10
---

# Plotting indicators
Indicators and associated signals can be easily plotted using the 
`plot_indicator(ctx, name, x, y, signals)` keyword.

Where:
- `name`: name of the indicator on the chart 
- `x`: values to use for the x axis
- `y`: values to use for the y axis
- `signal`: (optional) x values for which a signal is fired

Example where the goal is to plot the value of the rsi indicator from 
the [example script](/guides/octobot-script#script-example-rsi-strategy).
``` python
await obs.plot_indicator(ctx, "RSI", time_values, indicator_values, signal_times)
```
