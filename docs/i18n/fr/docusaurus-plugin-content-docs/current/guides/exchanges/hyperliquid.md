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
<div style={{textAlign: "center"}}>
  ![hyperliquid go to api settings](/images/guides/hyperliquid/hyperliquid-go-to-api-settings.png)
</div>
2. Créez une nouvelle clé API: 
  - Entrez un nom pour votre clé
  - Cliquez sur "Générer" pour créer une adresse aléatoire
<div style={{textAlign: "center"}}>
  ![hyperliquid api enter name and generate](/images/guides/hyperliquid/hyperliquid-api-enter-name-and-generate.png)
</div>
  - Autorisez le portefeuille API
<div style={{textAlign: "center"}}>
  ![hyperliquid api click authorize](/images/guides/hyperliquid/hyperliquid-api-click-authorize.png)
</div>
3. Définissez la durée maximale de validité en cliquant sur `MAX`
<div style={{textAlign: "center"}}>
  ![hyperliquid add api days and copy private key](/images/guides/hyperliquid/hyperliquid-add-api-days-and-copy-private-key.png)
</div>
4. Copiez la clé privée dans le champ `API Secret` d'Hyperliquid dans OctoBot
5. Autorisez votre clé API (cela peut nécessiter une signature de votre portefeuille)
<div style={{textAlign: "center"}}>
  ![hyperliquid api click authorize from popup](/images/guides/hyperliquid/hyperliquid-api-click-authorize-from-popup.png)
</div>
6. Copiez la clé publique de votre compte Hyperliquid dans le champ `API Key` d'Hyperliquid dans OctoBot et cliquez sur `Save`
<div style={{textAlign: "center"}}>
  ![hyperliquid copy public key](/images/guides/hyperliquid/hyperliquid-copy-public-key.png)
</div>

Votre compte Hyperliquid est maintenant connecté à votre OctoBot.
