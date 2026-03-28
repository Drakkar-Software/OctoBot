---
title: "Connecting to Coinbase"
description: "Step by step guide on how to securely use your Coinbase account with OctoBot cloud and profit from automated crypto investments."
sidebar_position: 24
---



# Connecting your Coinbase account to OctoBot cloud

To automate the investment strategies of your choice on your Coinbase account, it is necessary to allow OctoBot to access a part of your account.

This is done using `API Keys`. API Keys are a standard authentication system that is often used to connect software together.

If you are wondering what an `API Key` is and why OctoBot is using it, checkout our [introduction to exchanges API Keys](what-is-an-exchange-api-key).

## Connecting to your Coinbase account with API Keys

Here are the 5 simple steps to connect to your Coinbase account with OctoBot cloud and automate your investment strategies.

### 1. Log in to your Coinbase account

Go to <a href="https://login.coinbase.com/signin" rel="nofollow">coinbase.com</a> and log in to your account (or create an account).

![coinbase account login](/images/guides/coinbase/coinbase-account-login.png)

### 2. Go to API Management

Display your account settings by clicking on your account icon and select "Settings".
![account setting api management](/images/guides/coinbase/account-setting-api-management.png)

### 3. Create a new API Key

Scroll down if necessary and hit "API".

![account setting api management click api](/images/guides/coinbase/account-setting-api-management-click-api.png)

Click "Create API Key with Coinbase Developer Platform (Recommended)".

![apis list create new api](/images/guides/coinbase/apis-list-create-new-api.png)

1. Name it as you wish. The name is just for you to remember the purpose of this key.

2. Select the wallet you wish to use with your OctoBot. Note: the "Default" Coinbase wallet usually contains your funds on the regular (non Advanced) version of Coinbase. Please transfer your funds to another Coinbase wallet and select it with your API key if you wish to use different funds. 

3. **Remember to check the "Trade" API-specific restriction.**

![select api name passphrase and restrictions](/images/guides/coinbase/select-api-name-and-restrictions.png)

4. Click the "copy" button from OctoBot cloud to copy the IP whitelist and paste the list in the `IP whitelist` field.

### 4. Save your API Key

Now that your key is named, the Spot Trading permission is checked and the IP whitelist is configured, click "Create & download".  
Proceed with the security verification to create the API Key.

Your API Key is now created. Do not close this window as long as you are not done entering it on OctoBot cloud.

<div style="text-align: center">

![coinbase api key created](/images/guides/coinbase/coinbase-api-key-created.png)

</div>

Note: Coinbase will ask you to download a file containing the API Key details. Downloading it is not necessary, do not download the file or remove it from your computer if you did.

### 5. Add your API Key to your OctoBot cloud account

You now have your API key details !

All you need to do is to copy and paste the values of `API key name` and `Secret` (step 4) into your Coinbase account configuration on OctoBot cloud. This can be done either when starting a trading strategy with a real account or from your profile on [octobot.cloud](https://www.octobot.cloud/)

Note: When adding an API Key on OctoBot cloud, you can associate a name to it. As for the naming on Coinbase side, this is a free field where you can enter any name to quickly identify this API Key in the future.

<div style="text-align: center">

![api creation completed selected values](/images/guides/coinbase/api-creation-completed-selected-values.png)

</div>

![add API Key to octobot cloud from strategy start](/images/guides/coinbase/add-api-key-to-octobot-cloud-from-strategy-start.png)

<div style="text-align: center">
  <em>Adding an API Key when starting a strategy</em>
</div>

![add API Key to octobot cloud from profile](/images/guides/coinbase/add-api-key-to-octobot-cloud-from-profile.png)

<div style="text-align: center">
  <em>Adding an API Key directly from <a href="https://www.octobot.cloud/account" rel="nofollow">your profile</a></em>
</div>

Your Coinbase account can now be used on OctoBot cloud !

:::info
  Please note that when starting a bot, some of the funds available in your API key related portfolio might be sold. This include any stablecoin and fiat related funds as well as cryptocurrencies that are traded by the strategy you selected. This is is part of the [portfolio optimization](invest-with-your-strategy#1-portfolio-optimization).
:::

## Troubleshooting

### Incorrect API Keys

If you get the `Incorrect API Keys` error, this usually means that:

- There was an error when copy-pasting your API Key or Secret Key from Coinbase to OctoBot cloud
- You made a mistake when copying the IP whitelist
- You might have selected the wrong exchange (make sure to select Coinbase)
- Should you use ECDSA or Ed25519 API keys? You can use any, both ECDSA and Ed25519 key formats are supported.

### Incorrect API restrictions: missing spot trading

If you get the `Incorrect API restrictions: missing spot trading` error, you need to check "Trade" as explained [on step 3](#3-create-a-new-api-key).

### Incorrect API restrictions: withdrawals enabled

If you get the `Incorrect API restrictions: withdrawals enabled` error, you need to uncheck "Transfer". You can do this following the same path as [on step 3](#3-create-a-new-api-key).

### Other questions

If you have any other question of if something is unclear, feel free to reach out to the support using the chatbox on the bottom right of the screen on [octobot.cloud](https://www.octobot.cloud/).
