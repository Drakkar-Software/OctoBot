Binance is a RestExchange adaptation for Binance exchange using the REST API. 

# Binance account setup

## Create an account

- Fill <a href="https://accounts.binance.com/en/register?ref=528112221" rel="nofollow">this Binance</a> registration form

## Generate API key

If you are wondering what an `API Key` is and why OctoBot is using it, checkout our [introduction to exchanges API Keys](/investing/what-is-an-exchange-api-key).

### Generate Your Keys

- Sign into your Binance account
- Click on your profile in the top right corner
- Click on `API Management`

![Binance-Create-API-Key](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/docs/Binance/create_api_key.png)

### Configure the API Settings

- Give a label to your API Key.

![Binance-Name-API-Key](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/docs/Binance/name_api_key.png)

- Binance will ask a security confirmation to continue.
- OctoBot needs the `Enable Reading` permission to be able to pull in balances from Binance and `Enable Spot & Margin Trading` permission to create new orders. Click on `Edit restrictions` to enable `Enable Spot & Margin Trading`.

![Binance-created-API-Key](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/docs/Binance/created.png)

![Binance-Updated-API-Key](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/docs/Binance/allow_trade.png)

- Click on `Save` save the permission update.

![Binance-Final-API-Key](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/docs/Binance/final.png)

## Add the API key to OctoBot

### Add Binance exchange

- Start your OctoBot
- Click on `Accounts` tab
- Click on `Exchanges` on the left menu
- Click on the selector and search `Binance`
- Click on `ADD`

### Add Binance API keys

- Copy and paste `API Key` from Binance to your OctoBot `API Key` field
- Copy and paste `Secret Key` from Binance to your OctoBot `API Secret` field
- Leave the `API Password` as is

![OctoBot-Validate-Credentials](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/docs/Binance/enter_binance.png)
