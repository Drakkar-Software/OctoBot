---
title: "Configuration de compte"
description: "Découvrez comment vous connecter à la plateforme d'échange HollaEx de votre choix et automatiser vos stratégies avec OctoBot"
sidebar_position: 1
---



# Configuration de compte HollaEx

:::info
  La traduction française de cette page est en cours.
:::

> HollaEx is an open-source white label exchange: OctoBot is compatible with every HollaEx powered exchange.

An API Key can be considered as a username that is generating to allow access to data.

An API Secret, also referred to as API Private Key is simply a password used in combination with an API Key.

## Créer un compte

- Fill the on the HollaEx powered exchange you wish to trade on (or on <a href="https://hollaex.com" rel="nofollow">hollaex.com</a> to use HollaEx's demo exchange).

## Générer ses clés d'API

### Générer ses clés

- Sign into your Exchange account
- Click on your profile in the top right corner.
- Click on `Security`
- Click on `API Keys`
- Click on `Generate API Key`

![HollaEx-Create-API-Key](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/docs/HollaEx/HollaEx-My-Api.png)

### Configurer ses clés d'API

- Give a name to your API Key
- OctoBot needs the `Read` function to be able to pull in balances from HollaEx and `Trade` to create new orders.
- Click on Submit.

![HollaEx-Name-API-Key](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/docs/HollaEx/HollaEx-Create-key.png)

## Ajouter ses clés d'API sur OctoBot

### Ajouter son compte HollaEx

- Start your OctoBot
- Click on `Accounts` tab
- Click on `Exchanges` on the left menu
- Click on the selector and search `hollaex`
- Click on `ADD`

### Entrer l'adresse de la plateforme d'échange HollaEx

Optional: If you are connecting to an exchange that is based on HollaEx but is not https://www.hollaex.com/, you can enter its url on the HollaEx configuration.

![HollaEx-open-config](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/docs/HollaEx/HollaEx-OctoBot-open-exchange-config.png)

![HollaEx-url-config](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/docs/HollaEx/HollaEx-url-config.png)

Note: after changing the url, you will need to restart OctoBot for it to take your new exchange url into account.

### Ajouter ses clés d'API HollaEx

- Copy and paste `API Key` from HollaEx to your OctoBot `API Key` field
- Copy and paste `Secret Key` from HollaEx to your OctoBot `API Secret` field
  ![OctoBot-Validate-Credentials](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/docs/HollaEx/HollaEx-OctoBot-Add-Exchange-Creds.png)
- Click on `Save And restart`
  ![OctoBot-Validate-Credentials](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/docs/HollaEx/HollaEx-Save-And-Restart.png)
