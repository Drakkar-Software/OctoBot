---
title: "Configuration de compte"
description: "Découvrez comment se connecter à votre compte Binance en utilisant une clé d'API. Utilisez notre lien d'invitation pour et supportez OctoBot"
sidebar_position: 1
---



# Configuration de compte Binance

:::info
  La traduction française de cette page est en cours.
:::

## Créer un compte

- Remplissez ce <a href="https://accounts.binance.com/en/register?ref=528112221" rel="nofollow">formulaire d'inscription Binance</a>

## Générer ses clés d'API

Si vous vous demandez ce qu'est une `API Key` et pourquoi OctoBot utilise cette méthode, jetez un œil  à notre [présentation des API Keys de plateformes d'échange](/investing/what-is-an-exchange-api-key).

### Générer ses clés

- Sign into your Binance account
- Click on your profile in the top right corner
- Click on `API Management`

![Binance-Create-API-Key](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/docs/Binance/create_api_key.png)

### Configurer ses clés d'API

- Give a label to your API Key.

![Binance-Name-API-Key](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/docs/Binance/name_api_key.png)

- Binance will ask a security confirmation to continue.
- OctoBot needs the `Enable Reading` permission to be able to pull in balances from Binance and `Enable Spot & Margin Trading` permission to create new orders. Click on `Edit restrictions` to enable `Enable Spot & Margin Trading`.

![Binance-created-API-Key](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/docs/Binance/created.png)

![Binance-Updated-API-Key](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/docs/Binance/allow_trade.png)

- Click on `Save` save the permission update.

![Binance-Final-API-Key](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/docs/Binance/final.png)

## Ajouter ses clés d'API sur OctoBot

### Ajouter son compte Binance

- Start your OctoBot
- Click on `Accounts` tab
- Click on `Exchanges` on the left menu
- Click on the selector and search `Binance`
- Click on `ADD`

### Ajouter ses clés d'API Binance

- Copy and paste `API Key` from Binance to your OctoBot `API Key` field
- Copy and paste `Secret Key` from Binance to your OctoBot `API Secret` field
- Leave the `API Password` as is

![OctoBot-Validate-Credentials](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/docs/Binance/enter_binance.png)
