---
title: "Configuration de compte"
description: "Découvrez comment vous connecter à votre compte OKX avec OctoBot. Utilisez notre lien d'invitation pour OKX et supportez le projet en créant votre compte avec"
sidebar_position: 1
---



# Configuration de compte OKX

:::info
  La traduction française de cette page est en cours.
:::

An API Key can be considered as a username that is generating to allow access to data.

An API Secret, also referred to as API Private Key is simply a password used in combination with an API Key.

An API Password, also referred to as `Passphrase`, is considered an extra layer of security that is generally user generated. In this instance, you can create an API password to lock the API Key and Secret created on the OKX website. You will only be able to see your API Key and Secret by inputting the password you selected.

## Créer son compte sur OKX

- Remplissez ce <a href="https://www.okx.com/join/9403477" rel="nofollow">formulaire d'inscription OKX</a>

## Générer ses clés d'API

Si vous vous demandez ce qu'est une `API Key` et pourquoi OctoBot utilise cette méthode, jetez un œil  à notre [présentation des API Keys de plateformes d'échange](/investing/what-is-an-exchange-api-key).

### Générer ses clés

- Sign into your OKX account
- Click on your profile in the top right corner.
- Click on the `API`
- Click on `Create V5 API Key`

![OKX-Create-API-Key](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/docs/OKEx/OKEX-My-Api.png)

### Configurer ses clés d'API

- Give a name to your API Key, and set a Passphrase.
  > Make sure to remember that Passphrase, as you will need to use it again in a few moments.
- OctoBot needs the `Read` function to be able to pull in balances from OKX and `Trade` to create new orders.
- Click on Confirm, then click on `View` to see your API Key and API Secret.

![OKX-Configure-API-Key](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/docs/OKEx/OKEX-Create-v5-key.png)

## Ajouter ses clés d'API sur OctoBot

### Ajouter son compte OKX

- Start your OctoBot
- Click on `Accounts` tab
- Click on `Exchanges` on the left menu
- Click on the selector and search `okx`
- Click on `ADD`

![OctoBot-Add-Exchange](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/docs/OKEx/OKEx-OctoBot-Add-Exchange.png)

### Ajouter ses clés d'API OKX

- Copy and paste `API Key` from OKX to your OctoBot `API Key` field
- Copy and paste `Secret Key` from OKX to your OctoBot `API Secret` field
- Enter your OKX `API Password` to OctoBot `API Password` field
  ![OctoBot-Validate-Credentials](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/docs/OKEx/OKEx-OctoBot-Add-Exchange-Creds.png)
- Click on `Save And restart`
  ![OctoBot-Validate-Credentials](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/docs/OKEx/OKEx-Save-And-Restart.png)
