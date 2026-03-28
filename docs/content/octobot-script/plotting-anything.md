---
title: "Plotting anything"
description: "Learn how to plot any type of data on your strategy run report with python using OctoBot script."
sidebar_position: 11
---



# Plotting anything

Anything can be plotted on your strategy run report using the `plot(ctx, name, ...)` keyword.
The plot arguments are converted into <a href="https://plotly.com/javascript/" rel="nofollow">plotly</a> charts parameters.

Where:

- `name`: name of the indicator on the chart

Optional arguments:

- `x`: values to use for the x axis
- `y`: values to use for the y axis
- `z`: values to use for the z axis
- `text`: point labels
- `mode`: plotly mode ("lines", "markers", "lines+markers", "lines+markers+text", "none")
- `chart`: "main-chart" or "sub-chart" (default is "sub-chart")
- `own_yaxis`: when True, uses an independent y axis for this plot (default is False)
- `color`: color the of plot
- `open`: open values for a candlestick chart
- `high`: high values for a candlestick chart
- `low`: low values for a candlestick chart
- `close`: close values for a candlestick chart
- `volume`: volume values for a candlestick chart
- `low`: low values for a candlestick chart

Example:

```python
await obs.plot(ctx, "RSI", x=time_values, y=indicator_values, mode="markers")
```
