---
title: "Connecting to Kucoin"
description: "Step by step guide on how to securely use your Kucoin account with OctoBot cloud and profit from automated crypto investments."
sidebar_position: 23
---



# Connecting your Kucoin account to OctoBot cloud

To automate the investment strategies of your choice on your Kucoin account, it is necessary to allow OctoBot to access a part of your account.

This is done using `API Keys`. API Keys are a standard authentication system that is often used to connect software together.

If you are wondering what an `API Key` is and why OctoBot is using it, checkout our [introduction to exchanges API Keys](what-is-an-exchange-api-key).

## Connecting to your Kucoin account with API Keys

Here are the 5 simple steps to connect to your Kucoin account with OctoBot cloud and automate your investment strategies.

### 1. Log in to your Kucoin account

Go to <a href="https://www.kucoin.com/ucenter/signup?rcode=rJ2Q2T3" rel="nofollow">kucoin.com</a> and log in to your account (or create an account).

![kucoin account login](/images/guides/kucoin/kucoin-account-login.png)

### 2. Go to API Management

Display your account dashboard by clicking on your account and select "API Management".
![account setting api management](/images/guides/kucoin/account-setting-api-management.png)

### 3. Create a new API Key

1. Click "Create API", select "API-Based Trading".

2. Name it as you wish and give it a passphrase. The name is just for you to remember the purpose of this key. The passphrase will have to be entered alongside your API key details on OctoBot cloud.

3. **Remember to check the "Spot Trading" API Restriction**.

![apis list create new api](/images/guides/kucoin/apis-list-create-new-api.png)

![select api name passphrase and restrictions](/images/guides/kucoin/select-api-name-passphrase-and-restrictions.png)

4. Select the `Restrict to Trusted IPs Only` option.

5. Click the "copy" button from OctoBot cloud to copy the IP whitelist and paste the list in the IP whitelist field, then click `Add`.


### 4. Save your API Key

Now that your key is named, has a passphrase and the Spot Trading permission is selected, click "Next"

Proceed with the security verification to create the API Key.

<div style="text-align: center">

![create api security verification](/images/guides/kucoin/create-api-security-verification.png)

</div>

Your API Key is now created. Do not close this window as long as your are not done entering it on OctoBot cloud.

<div style="text-align: center">

![kucoin api key created](/images/guides/kucoin/kucoin-api-key-created.png)

</div>

### 5. Add your API Key to your OctoBot cloud account

You now have your API key details !

All you need to do is to copy and paste the values of `Key`, `Secret` (step 4) and the passphrase (step 3) into your Kucoin account configuration on OctoBot cloud. This can be done either when starting a trading strategy with a real account or from your profile on [octobot.cloud](https://www.octobot.cloud/)

Note: When adding an API Key on OctoBot cloud, you can associate a name to it. As for the naming on Kucoin side, this is a free field where you can enter any name to quickly identify this API Key in the future.

<div style="text-align: center">

![api creation completed selected values](/images/guides/kucoin/api-creation-completed-selected-values.png)

</div>

![add API Key to octobot cloud from strategy start](/images/guides/kucoin/add-api-key-to-octobot-cloud-from-strategy-start.png)

<div style="text-align: center">
  <em>Adding an API Key when starting a strategy</em>
</div>

![add API Key to octobot cloud from profile](/images/guides/kucoin/add-api-key-to-octobot-cloud-from-profile.png)

<div style="text-align: center">
  <em>Adding an API Key directly from <a href="https://www.octobot.cloud/account" rel="nofollow">your profile</a></em>
</div>

Your Kucoin account can now be used on OctoBot cloud !

:::info
  Please note that when starting a bot, some of the funds available in your API key related portfolio might be sold. This include any stablecoin and fiat related funds as well as cryptocurrencies that are traded by the strategy you selected. This is is part of the [portfolio optimization](invest-with-your-strategy#1-portfolio-optimization).
:::

## Troubleshooting

### Incorrect API Keys

If you get the `Incorrect API Keys` error, this usually means that:

- There was an error when copy-pasting your API Key, Secret Key or passphrase from Kucoin to OctoBot cloud
- You made a mistake when copying the IP whitelist
- You might have selected the wrong exchange (make sure to select Kucoin)

### Incorrect API restrictions: missing spot trading

If you get the `Incorrect API restrictions: missing spot trading` error, you need to check "Spot Trading" as explained [on step 3](#3-create-a-new-api-key).

### Incorrect API restrictions: withdrawals enabled

If you get the `Incorrect API restrictions: withdrawals enabled` error, you need to uncheck "Transfer". You can do this following the same path as [on step 3](#3-create-a-new-api-key).

### Other questions

If you have any other question of if something is unclear, feel free to reach out to the support using the chatbox on the bottom right of the screen on [octobot.cloud](https://www.octobot.cloud/).
