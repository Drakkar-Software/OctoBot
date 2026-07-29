---
title: "Get started with OctoBot beta"
description: "Start OctoBot in node mode, connect your wallet and node to the new OctoBot interface, and run automations or manual OctoBot instances from one place."
sidebar_position: 8
---



# Get started with OctoBot beta

:::info
OctoBot beta is work in progress. You may hit bugs or incomplete features.
:::

OctoBot beta is the open-source OctoBot with a new system for portfolio automation from desktop and mobile. You run it on your computer or server in **node mode** (the new default OctoBot mode), which acts as the backend for the **new OctoBot interface**.

<div style="text-align: center">

![OctoBot beta welcome screen](/images/guides/octobot-beta/OctoBot-beta-welcome-screen.png)

</div>

## Download and start your node

1. Get the latest beta from the <a href="https://github.com/Drakkar-Software/OctoBot/releases/latest" rel="nofollow">GitHub releases page</a>
2. Install on your computer or server using the [install guide](octobot-installation/install-octobot-on-your-computer) (executable, Docker, or Python)

Starting the latest release runs OctoBot in **node mode**. Complete the initial node setup on first launch. From one node, you can run multiple automations (DCA, Grid, crypto basket) and [manual OctoBot](#start-a-manual-octobot-from-your-node) instances.

## Connect the new OctoBot interface to your node

### Mobile and web browser access

You can connect to your node in two ways:

1. **Web browser:** Open the <a href="https://new.mobile.octobot.cloud/home" rel="nofollow">new OctoBot interface</a> on desktop or mobile (recommended).
2. **Android app (optional):** Install the beta app from the <a href="https://play.google.com/store/apps/details?id=com.drakkarsoftware.octobotapp" rel="nofollow">Google Play Store</a>. Enable the app's beta program on the Play Store to use it.

<div style="text-align: center">

![Connect the new OctoBot interface to your node by entering its hostname or IP](/images/guides/octobot-beta/connected-OctoBot-node-to-the-octobot-ui.png)

</div>

### Follow the node's initial configuration guide

On first launch, your node opens a built-in initial configuration guide. Follow it to connect the new OctoBot interface to your node. It covers wallet setup and the connection steps.

Use the <a href="https://new.mobile.octobot.cloud/home" rel="nofollow">new OctoBot interface</a> to manage your OctoBots, and link your exchange accounts. Your node will be your secure server running your strategies.

### Manual setup (if necessary)

If you skipped the initial configuration guide or need to connect again later, set this up manually:

#### Step 1: Add your wallet to the new OctoBot interface

1. On the node, open **Settings** → **Wallet management**
2. Export your **wallet private key**
3. In the new OctoBot interface or Android beta app, paste the private key to load your wallet

#### Step 2: Connect to your node

Follow the OctoBot interface connection guide available from the settings of your node.

## Starting OctoBots from the new OctoBot interface

Once connected, the home dashboard shows your accounts and running automations.

<div style="text-align: center">

![OctoBot beta home dashboard with connected accounts and automations](/images/guides/octobot-beta/OctoBot-beta-default-home-with-3-accounts-and-3-automations.png)

</div>

**Automations** are the new way to run OctoBots. An automation is a **strategy** running on OctoBot. It can do anything: DCA, baskets, grids, TradingView automation, and more. Automations support demo and live trading. You can start as many as you want from the new OctoBot interface.

Soon, we will introduce a **Graphic strategy editor** to configure any type of automation and custom algorithm in the new OctoBot interface, making configuration effectively unlimited.

## Start a manual OctoBot from your node

For backtesting, Telegram, TradingView, and other advanced workflows, start a **manual OctoBot** instance from the new OctoBot interface.

1. Open your OctoBot node interface
2. Click **New OctoBot**
3. Follow the prompts to start a manual OctoBot instance

<div style="text-align: center">

![Start a manual OctoBot from the node by clicking New OctoBot](/images/guides/octobot-beta/OctoBot-node-start-manual-octobot.png)

</div>

See the [open-source guides](octobot) for configuration, trading modes, and interfaces.

## Connect from anywhere with Tailscale

If your node runs on a computer, server, or Raspberry Pi and you want to manage it from the new OctoBot interface or Android beta app anywhere, use a <a href="https://tailscale.com/download" rel="nofollow">Tailscale</a> private network instead of exposing your node on the public internet.

Tailscale is a leading private networking provider. It is free for personal use and built on open-source software.

1. Download Tailscale and create a Tailscale account
2. Install Tailscale on the computer or server running your OctoBot node
3. Install Tailscale on your mobile device
4. Enable Tailscale on both your devices: your Tailscale app should display your server and your mobile as **Connected**
5. Use your node's **Tailscale IP address or MagicDNS** when connecting the new OctoBot interface to your node

:::info
**Pro tip:** Tailscale lets you run your node on any machine and control it from the new OctoBot interface or Android beta app over a secure private network.
:::

## Connection troubleshooting

If you cannot connect the new OctoBot interface to your node, check these known issues:

- Your node server must accept incoming connections. Your network may need to be tagged as a trusted network, or your firewall might block connections. When using Tailscale, your Tailscale network may also need to be tagged as trusted to accept connections.
- Your antivirus could prevent incoming connections as well. If so, try temporarily disabling it when connecting to your node. If that works, add the OctoBot executable as an exception in your antivirus.

## Share feedback

OctoBot beta is actively evolving. Your feedback helps us improve what ships in the official release.

Join us on <a href="https://t.me/octobot_trading" rel="nofollow">Telegram</a> or <a href="https://discord.com/invite/vHkcb8W" rel="nofollow">Discord</a>. We read every message.
