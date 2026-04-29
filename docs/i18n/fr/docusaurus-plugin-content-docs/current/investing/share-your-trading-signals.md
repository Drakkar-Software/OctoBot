---
title: "Partagez vos signaux de trading"
description: "Apprenez comment partager vos signaux de trading crypto sur OctoBot cloud pour permettre à d'autres de copier automatiquement vos signaux."
sidebar_position: 27
---



# Partager vos signaux de trading

## Partager des signaux de trading depuis Telegram

L'intégration du bot Telegram d'OctoBot vous permet de partager des signaux de trading depuis votre groupe Telegram.
Vous pouvez choisir entre deux formats de signaux :

- Format OctoBot (similaire au format d'[alerte personnalisée de TradingView](tradingview-alerts-automation#automatisations-tradingview-personnalisées))
- Format Cornix

### Étapes pour configurer le bot Telegram

1. **Ouvrir la vue de gestion des stratégies**

- Rendez-vous sur la <a href="https://www.octobot.cloud/creator" rel="nofollow">page de gestion des stratégies</a>, dans la section `Administration`
- Sélectionnez la stratégie pour laquelle vous souhaitez partager des signaux

2. **Ajouter OctoBot à votre groupe Telegram**

Ajoutez le bot Telegram d'OctoBot à votre groupe Telegram en tant qu'administrateur. Cela permet au bot de récupérer les signaux de trading du groupe.  
Vous pouvez trouver le bot en recherchant son nom dans Telegram et en l'ajoutant à votre groupe avec des privilèges d'administrateur.

3. **Récupérer l'ID du canal**

Transférez un message de votre groupe Telegram à `@getidsbot` pour obtenir l'ID du canal. L'ID du canal sera un nombre négatif, par exemple `-1000000000000`.  
Copiez cet ID de canal pour l'utiliser à l'étape suivante.

4. **Activer l'intégration Telegram et saisir l'ID du canal**

Dans la section "Intégrations" de votre stratégie OctoBot, trouvez l'onglet **Telegram** et activez-le en basculant l'interrupteur sur la position "on".  
Dans le champ "ID du canal", collez l'ID du canal que vous avez récupéré (par exemple, `-1000000000000`). Cela indique à OctoBot où lire les signaux de trading.

5. **Sélectionner le type de signal**

Choisissez le format des signaux de trading à partager dans votre groupe Telegram :

- **Format OctoBot** : Le format par défaut, similaire au format d'alerte personnalisé de TradingView, utilisé par OctoBot pour partager des signaux.
- **Format Cornix** : Le même format que Cornix.
- Utilisez le menu déroulant "Type de signal" pour sélectionner votre format préféré.

## Gérer les utilisateurs de la stratégie avec un l'interface HTTP

L'interface HTTP vous permet de gérer les utilisateurs de votre stratégie en ajoutant des ID externes et en définissant des dates d'expiration. Cette procédure est nécessaire pour les stratégies privées.

### Étapes pour gérer les utilisateurs avec l'interface HTTP

1. **Configurer le contrôle d'accès pour votre stratégie**

Dans la section "Contrôle d'accès", choisissez entre "Stratégie publique" et "Stratégie privée". Pour gérer les utilisateurs via HTTP, sélectionnez **Stratégie privée** pour activer la gestion des membres.

- Stratégie publique : Tout le monde peut accéder et utiliser la stratégie sans gestion des membres.
- Stratégie privée : Seuls les membres approuvés peuvent accéder à la stratégie, nécessitant une gestion des membres.

2. **Copier l'URL HTTP**

Dans la section "Intégrations", copiez le **l'URL HTTP** et collez-le dans votre code. Cela vous permet d'envoyer des signaux de trading ou de gérer les membres via des requêtes HTTP.

3. **Générer une clé API**

Cliquez sur le bouton **Créer une nouvelle clé API** pour générer une clé API unique pour vos requêtes HTTP. Cette clé sera utilisée pour authentifier vos requêtes.

**Avertissement** : Les clés API ne sont affichées qu'une seule fois. Elles ne doivent jamais être partagées.

4. **Ajouter la clé secrète API à votre requête HTTP**

Incluez la clé API **secrète** dans l'en-tête de votre requête HTTP sous la forme `Your-API-Key`.

Par exemple, pour gérer des membres avec des ID Telegram :

```
curl -X POST https://services.octobot.cloud/cloud/creator/webhook/AAAAA-BBBBBBB/CCCCCCC-DDDDDDDD/members/telegram -d '{"user_id": "USER_ID", "expiration_date": "EXPIRATION_DATE"}' -H 'Content-Type: application/json' -H 'Api-Key: XXXXXXXXXXX-YYYYYYYYYYY'
```

Avec :

- `USER_ID` : L'ID utilisateur Telegram du membre que vous souhaitez ajouter ou mettre à jour (pas son Telegram handle).
- `EXPIRATION_DATE` : La date jusqu'à laquelle le membre a accès à la stratégie (par exemple, 2025-12-31).
