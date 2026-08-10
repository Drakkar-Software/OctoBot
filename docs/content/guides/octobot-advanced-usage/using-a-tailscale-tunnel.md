---
title: "Using a Tailscale tunnel"
description: "Use the Tailscale tunnel CLI to expose your OctoBot's webhook port to the Internet, for example to use it as a TradingView webhook."
sidebar_position: 4
---



# Using a Tailscale tunnel with OctoBot

## Why using a Tailscale tunnel with your OctoBot

If you want to send [webhook](/guides/octobot-interfaces/tradingview/using-a-webhook) messages to your OctoBot (for example from TradingView), your OctoBot needs to be reachable from the Internet. Instead of using the [Premium OctoBot Extension](/guides/octobot-configuration/premium-octobot-extension) or Ngrok, you can use <a href="https://tailscale.com/kb/1223/tailscale-funnel/" rel="nofollow">Tailscale Funnel</a> to expose your OctoBot's webhook port with a stable public URL and HTTPS, without opening any port on your router.

## How to expose your OctoBot's webhook port with Tailscale

1.  Install the <a href="https://tailscale.com/download" rel="nofollow">Tailscale CLI</a> on the machine running your OctoBot and log in:

    ```bash
    tailscale up
    ```

2.  Set up your OctoBot's webhook manually: in your OctoBot configuration, from the `Accounts` tab, in `Interfaces`, add the webhook service, disable both `Enable-Ngrok` and `Enable-Octobot-Webhook`, and configure the listening port (`9000` by default) and IP for the webhook yourself. See [manual webhook configuration](/guides/octobot-interfaces/tradingview/using-a-webhook#setting-up-your-octobots-webhook) for details.

3.  Expose that port to the Internet with `tailscale funnel`, replacing `9000` with your webhook port:

    ```bash
    tailscale funnel 9000
    ```

    Tailscale prints the public HTTPS URL your OctoBot is now reachable at, such as `https://your-machine.your-tailnet.ts.net/`.

4.  Use this URL, with your OctoBot's webhook path appended, as your TradingView webhook URL.

5.  Activate a tentacle using a webhook service (like the TradingView signals trading mode) and restart your OctoBot.

:::info
  `tailscale funnel` keeps running in the foreground by default. Add `--bg` to run it in the background and keep the tunnel up after closing your terminal: `tailscale funnel --bg 9000`.
:::

:::info
  **Using docker?** When running your OctoBot in a Docker container, also add `-p 9000:9000` after `docker run` so the webhook port is reachable from the host machine that runs `tailscale funnel`.
:::

## Funnel vs Serve

- `tailscale funnel` exposes your OctoBot's webhook port to the **public Internet**, which is what you need for TradingView to reach it.
- `tailscale serve` only exposes it to devices on your own <a href="https://tailscale.com/kb/1136/tailnet/" rel="nofollow">tailnet</a>, which is enough if you only need to reach your OctoBot's webhook from your own devices.

Follow [this guide](/guides/octobot-interfaces/tradingview) to know more on how to send TradingView signals to your OctoBot.
