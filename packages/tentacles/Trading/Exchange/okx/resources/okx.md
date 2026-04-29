Okx is a basic RestExchange adaptation for OKX exchange. 

# OKX account setup

An API Key can be considered as a username that is generating to allow access to data.

An API Secret, also referred to as API Private Key is simply a password used in combination with an API Key.

An API Password, also referred to as `Passphrase`, is considered an extra layer of security that is generally user generated. In this instance, you can create an API password to lock the API Key and Secret created on the OKX website. You will only be able to see your API Key and Secret by inputting the password you selected.

## Create an account on OKX

- Fill <a href="https://www.okx.com/join/9403477" rel="nofollow">this OKX</a> registration form

## Generate API key

If you are wondering what an `API Key` is and why OctoBot is using it, checkout our [introduction to exchanges API Keys](/investing/what-is-an-exchange-api-key).

### Generate Your Keys

- Sign into your OKX account
- Click on your profile in the top right corner.
- Click on the `API`
- Click on `Create V5 API Key`

![OKX-Create-API-Key](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/docs/OKEx/OKEX-My-Api.png)

### Configure the API Settings

- Give a name to your API Key, and set a Passphrase.
  > Make sure to remember that Passphrase, as you will need to use it again in a few moments.
- OctoBot needs the `Read` function to be able to pull in balances from OKX and `Trade` to create new orders.
- Click on Confirm, then click on `View` to see your API Key and API Secret.

![OKX-Configure-API-Key](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/docs/OKEx/OKEX-Create-v5-key.png)

## Add the API key to OctoBot

### Add OKX exchange

- Start your OctoBot
- Click on `Accounts` tab
- Click on `Exchanges` on the left menu
- Click on the selector and search `okx`
- Click on `ADD`

![OctoBot-Add-Exchange](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/docs/OKEx/OKEx-OctoBot-Add-Exchange.png)

### Add OKX API keys

- Copy and paste `API Key` from OKX to your OctoBot `API Key` field
- Copy and paste `Secret Key` from OKX to your OctoBot `API Secret` field
- Enter your OKX `API Password` to OctoBot `API Password` field
  ![OctoBot-Validate-Credentials](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/docs/OKEx/OKEx-OctoBot-Add-Exchange-Creds.png)
- Click on `Save And restart`
  ![OctoBot-Validate-Credentials](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/docs/OKEx/OKEx-Save-And-Restart.png)
