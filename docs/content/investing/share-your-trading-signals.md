---
title: "Share your trading signals"
description: "Learn how to share your crypto trading signals on OctoBot cloud and let others automatically copy your signals."
sidebar_position: 27
---



# Share your trading signals

## Sharing trading signals from Telegram

The OctoBot Telegram bot integration allows you to share trading signals from your Telegram group.
You can choose between two signal formats:

- OctoBot format (aligned with [TradingView custom alert format](tradingview-alerts-automation#tradingview-custom-automations))
- Cornix format

### Steps to configure the Telegram Bot

1. **Open the strategy management view**

- Go to the <a href="https://www.octobot.cloud/creator" rel="nofollow">strategy management page</a>, in the `Administration` section
- Select the strategy for which you want to share signals

2. **Add OctoBot to Your Telegram Group**

Add the OctoBot Telegram bot to your Telegram group as an admin. This allows the bot to read trading signals from the group.  
You can find the bot by searching the bot name in Telegram and adding it to your group with admin privileges.

3. **Retrieve the Channel ID**

Forward a message from your Telegram group to `@getidsbot` to obtain the channel ID. The channel ID will be a negative number, such as `-1000000000000`.  
Copy this channel ID for use in the next step.

4. **Enable Telegram Integration and Enter the Channel ID**

In the "Integrations" section of your OctoBot strategy, locate the **Telegram** tab and enable it by toggling the switch to the "on" position.  
In the "Channel ID" field, paste the channel ID you retrieved (e.g., `-1000000000000`). This tells OctoBot where to read the trading signals.

5. **Select the Signal Type**

Choose the format for the trading signals to be shared in your Telegram group:

- **OctoBot Format**: The default format, aligned with TradingView custom alert format, used by OctoBot for sharing signals.
- **Cornix Format**: The same format as Cornix.
- Use the "Signal Type" dropdown menu to select your preferred format.

## Manage strategy users with HTTP Endpoint

The HTTP endpoint allows you to manage users of your strategy by adding external IDs and setting expiration dates. This is required for private strategies.

### Steps to manage users with HTTP Endpoint

1. **Set Up Access Control for Your Strategy**

In the "Access control" section, choose between "Public strategy" and "Private strategy." For managing users via HTTP, select **Private strategy** to enable member management.

- Public strategy: Anyone can access and use the strategy without member management.
- Private strategy: Only approved members can access the strategy, requiring member management.

2. **Copy the HTTP Endpoint**

In the "Integrations" section, copy the **HTTP endpoint** the paste it in your code. This allows you to send trading signals or manage members via HTTP requests.

3. **Generate an API Key**

Click on the **Create a new API key** button to generate API keys for your HTTP requests. This keys will be used to authenticate your requests.

**Warning**: API keys are shown only once. API keys should never be shared to anyone.

4. **Add the secret API Key to Your HTTP Request**

Include the **secret** API key in the header of your HTTP request as `Your-API-Key`.

For example, to manage members with telegram ids:

```
curl -X POST https://services.octobot.cloud/cloud/creator/webhook/AAAAA-BBBBBBB/CCCCCCC-DDDDDDDD/members/telegram -d '{"user_id": "USER_ID", "expiration_date": "EXPIRATION_DATE"}' -H 'Content-Type: application/json' -H 'Api-Key: XXXXXXXXXXX-YYYYYYYYYYY'
```

Where:

- `USER_ID`: The Telegram user ID of the member you want to add or update (not his telegram handle).
- `EXPIRATION_DATE`: The date until which the member has access to the strategy (e.g., 2025-12-31).
