---
title: "Connecting to Binance"
description: "Step by step guide on how to securely use your Binance account with OctoBot cloud and profit from automated crypto investments."
sidebar_position: 22
---



# Connecting your Binance account to OctoBot cloud

To automate the investment strategies of your choice on your Binance account, it is necessary to allow OctoBot to access a part of your account.

This is done using `API Keys`. API Keys are a standard authentication system that is often used to connect software together.

If you are wondering what an `API Key` is and why OctoBot is using it, checkout our [introduction to exchanges API Keys](what-is-an-exchange-api-key).

## Connecting to your Binance account with API Keys

Here are the 7 simple steps to connect to your Binance account with OctoBot cloud and automate your investment strategies.

### 1. Log in to your Binance account

Go to <a href="https://accounts.binance.com/en/register?ref=528112221" rel="nofollow">binance.com</a> and log in to your account (or create an account).

![binance account login](/images/guides/binance/binance-account-login.png)

### 2. Go to API Management

Select "Account" and "API Management" from your account Dashboard or "API Management" from top right profile icon dropdown menu.
![account setting api management](/images/guides/binance/account-setting-api-management.png)

![account api management from navbar](/images/guides/binance/account-api-management-from-navbar.png)

### 3. Create a new API Key

Hit "create API", select "System generated" and name it as you wish. The name is just for you to remember the purpose of this key.
![apis list create new api](/images/guides/binance/apis-list-create-new-api.png)

![select api type](/images/guides/binance/select-api-type.png)

![select api name](/images/guides/binance/select-api-name.png)

### 4. Security verification

Proceed with the security verification to create the API Key.
![create api security verification](/images/guides/binance/create-api-security-verification.png)

### 5. Add trading permissions and IP whitelisting

Your API Key is now created !

The only remaining thing is to add the trading permission for OctoBot to be able to create and cancel orders using this API Key. To do this: 

1. Click "Edit restrictions".

2. Choose "Restrict access to trusted IPs only"

3. Click the "copy" button from OctoBot cloud to copy the IP whitelist

4. Paste the list in the field that just appeared

5. Click "Confirm". 

6. Check "Enable Spot & Margin Trading". 

7. Finally click "Save".

![api created click edit restrictions](/images/guides/binance/api-created-click-edit-restrictions.png)

![api created add trading permission](/images/guides/binance/api-created-add-trading-permission.png)

![api created add trading permission save](/images/guides/binance/api-created-add-trading-permission-save.png)

![api restrict to trusted ips](/images/guides/binance/api-restrict-to-trusted-ips.png)

Please note that every other permission than "Enable Reading" and "Enable Spot & Margin Trading" should remain unchecked.

### 6. Add your API Key to your OctoBot cloud account

Your API Key is now ready to be used by OctoBot !

All you need to do is to copy and paste both `API Key` and `Secret Key` values into your Binance account configuration on OctoBot cloud. This can be done either when starting a trading strategy with a real account or from your profile on [octobot.cloud](https://www.octobot.cloud/)

Note: When adding an API Key on OctoBot cloud, you can associate a name to it. As for the naming on Binance side, this is a free field where you can enter any name to quickly identify this API Key in the future.
![api creation completed selected values](/images/guides/binance/api-creation-completed-selected-values.png)

![add API Key to octobot cloud from strategy start](/images/guides/binance/add-api-key-to-octobot-cloud-from-strategy-start.png)

<div style="text-align: center">
  <em>Adding an API Key when starting a strategy</em>
</div>

![add API Key to octobot cloud from profile](/images/guides/binance/add-api-key-to-octobot-cloud-from-profile.png)

<div style="text-align: center">
  <em>Adding an API Key directly from <a href="https://www.octobot.cloud/account" rel="nofollow">your profile</a></em>
</div>

Your Binance account can now be used on OctoBot cloud !

:::info
  Please note that when starting a bot, some of the funds available in your API key related portfolio might be sold. This include any stablecoin and fiat related funds as well as cryptocurrencies that are traded by the strategy you selected. This is is part of the [portfolio optimization](invest-with-your-strategy#1-portfolio-optimization).
:::


## Troubleshooting

### Incorrect API Keys

If you get the `Incorrect API Keys` error, this usually means that:

- There was an error when copy-pasting your API Key or Secret Key from Binance to OctoBot cloud
- You made a mistake when copying the IP whitelist
- You might have selected the wrong exchange (make sure to select Binance)

### Incorrect API restrictions: missing spot trading

If you get the `Incorrect API restrictions: missing spot trading` error, you need to check "Enable Spot & Margin Trading" as explained [on step 6](#6-add-trading-permissions).

### Incorrect API restrictions: withdrawals enabled

If you get the `Incorrect API restrictions: withdrawals enabled` error, you need to uncheck "Enable Withdrawals". You can do this following the same path as [on step 6](#6-add-trading-permissions).

### Other questions

If you have any other question of if something is unclear, feel free to reach out to the support using the chatbox on the bottom right of the screen on [octobot.cloud](https://www.octobot.cloud/).
