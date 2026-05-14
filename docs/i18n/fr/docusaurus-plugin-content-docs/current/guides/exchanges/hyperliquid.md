---
title: "Hyperliquid"
description: "Tradez sur les marchés spot de Hyperliquid avec OctoBot. Utilisez le trading virtuel ou vos fonds sur échange. Profitez de la connexion REST."
sidebar_position: 5
---

# Trader sur Hyperliquid

## Supporté par OctoBot

### Trading spot
| Trading spot | ✅  |
| :--- | :--- |
| Simulation | ✅ |
| REST | ✅  |
| Websocket | ✅  |
| Testnet | ❌  |

Veuillez noter que le trading de futures sur Hyperliquid n'est pas encore pris en charge par OctoBot.

### Connecter OctoBot à un compte Hyperliquid

Pour trader sur votre compte Hyperliquid avec OctoBot, vous devrez créer une clé API associée à votre compte Hyperliquid. Voici un guide étape par étape.

1. Connectez-vous à votre compte Hyperliquid et ouvrez les paramètres d'API

![hyperliquid go to api settings](/images/guides/hyperliquid/hyperliquid-go-to-api-settings.png)

2. Créez une nouvelle clé API: 
  - Entrez un nom pour votre clé
  - Cliquez sur "Générer" pour créer une adresse aléatoire

![hyperliquid api enter name and generate](/images/guides/hyperliquid/hyperliquid-api-enter-name-and-generate.png)

  - Autorisez le portefeuille API

![hyperliquid api click authorize](/images/guides/hyperliquid/hyperliquid-api-click-authorize.png)

3. Définissez la durée maximale de validité en cliquant sur `MAX`

![hyperliquid add api days and copy private key](/images/guides/hyperliquid/hyperliquid-add-api-days-and-copy-private-key.png)

4. Copiez la clé privée dans le champ `API Secret` d'Hyperliquid dans OctoBot
5. Autorisez votre clé API (cela peut nécessiter une signature de votre portefeuille)

![hyperliquid api click authorize from popup](/images/guides/hyperliquid/hyperliquid-api-click-authorize-from-popup.png)

6. Copiez la clé publique de votre compte Hyperliquid dans le champ `API Key` d'Hyperliquid dans OctoBot et cliquez sur `Save`

![hyperliquid copy public key](/images/guides/hyperliquid/hyperliquid-copy-public-key.png)

Votre compte Hyperliquid est maintenant connecté à votre OctoBot.
