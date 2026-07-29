---
title: "Démarrer avec OctoBot beta"
description: "Démarrez OctoBot en node mode, connectez votre wallet et votre node à la nouvelle interface OctoBot, et lancez des automatisations ou des instances OctoBot manuel."
sidebar_position: 8
---



# Démarrer avec OctoBot beta

:::info
OctoBot beta est en cours de développement. Vous pouvez rencontrer des bugs ou des fonctionnalités incomplètes.
:::

OctoBot beta est l'OctoBot open source avec un nouveau système pour l'automatisation de portefeuille depuis le bureau et le mobile. Vous l'exécutez sur votre ordinateur ou serveur en **node mode** (le nouveau mode OctoBot par défaut), qui sert de backend pour la **nouvelle interface OctoBot**.

<div style="text-align: center">

![Écran d'accueil OctoBot beta](/images/guides/octobot-beta/OctoBot-beta-welcome-screen.png)

</div>

## Télécharger et démarrer votre node

1. Récupérez la dernière beta sur la <a href="https://github.com/Drakkar-Software/OctoBot/releases/latest" rel="nofollow">page des releases GitHub</a>
2. Installez sur votre ordinateur ou serveur avec le [guide d'installation](octobot-installation/install-octobot-on-your-computer) (exécutable, Docker ou Python)

Le démarrage de la dernière release lance OctoBot en **node mode**. Complétez la configuration initiale du node au premier lancement. Depuis un seul node, vous pouvez exécuter plusieurs automatisations (DCA, Grid, panier crypto) et des instances [OctoBot manuel](#démarrer-un-octobot-manuel-depuis-votre-node).

## Connecter la nouvelle interface OctoBot à votre node

### Accès mobile et navigateur web

Deux façons de vous connecter à votre node :

1. **Navigateur web :** Ouvrez la <a href="https://new.mobile.octobot.cloud/home" rel="nofollow">nouvelle interface OctoBot</a> sur ordinateur ou mobile (recommandé).
2. **App Android (optionnel) :** Installez l'app beta sur le <a href="https://play.google.com/store/apps/details?id=com.drakkarsoftware.octobotapp" rel="nofollow">Google Play Store</a>. Activez le programme beta de l'app sur le Play Store pour l'utiliser.

<div style="text-align: center">

![Connecter la nouvelle interface OctoBot à votre node en entrant son nom d'hôte ou son adresse IP](/images/guides/octobot-beta/connected-OctoBot-node-to-the-octobot-ui.png)

</div>

### Suivre le guide de configuration initiale du node

Au premier lancement, votre node ouvre un guide de configuration initiale intégré. Suivez-le pour connecter la nouvelle interface OctoBot à votre node. Il couvre la configuration du wallet et les étapes de connexion.

Utilisez la <a href="https://new.mobile.octobot.cloud/home" rel="nofollow">nouvelle interface OctoBot</a> pour gérer vos OctoBots et connecter vos comptes d'exchange. Votre node sera votre serveur sécurisé qui exécute vos stratégies.

### Configuration manuelle (si nécessaire)

Si vous avez ignoré le guide de configuration initiale ou si vous devez vous reconnecter plus tard, configurez cela manuellement :

#### Étape 1 : Ajouter votre wallet à la nouvelle interface OctoBot

1. Sur le node, ouvrez **Settings** → **Wallet management**
2. Exportez votre **wallet private key**
3. Dans la nouvelle interface OctoBot ou l'app beta Android, collez la clé privée pour charger votre wallet

#### Étape 2 : Connecter votre node

Suivez le guide de connexion de l'interface OctoBot disponible depuis les paramètres de votre node.

## Démarrer des OctoBots depuis la nouvelle interface OctoBot

Une fois connecté, le tableau de bord d'accueil affiche vos comptes et automatisations en cours.

<div style="text-align: center">

![Tableau de bord OctoBot beta avec comptes connectés et automatisations](/images/guides/octobot-beta/OctoBot-beta-default-home-with-3-accounts-and-3-automations.png)

</div>

Les **automatisations** sont la nouvelle façon de faire tourner des OctoBots. Une automatisation est une **stratégie** exécutée sur OctoBot. Elle peut tout faire : DCA, paniers, grids, automatisation TradingView, et plus encore. Les automatisations supportent le trading en démo et en réel. Vous pouvez en démarrer autant que vous voulez depuis la nouvelle interface OctoBot.

Bientôt, nous introduirons un **éditeur graphique de stratégies** pour configurer tout type d'automatisation et d'algorithme personnalisé dans la nouvelle interface OctoBot, rendant la configuration quasiment illimitée.

## Démarrer un OctoBot manuel depuis votre node

Pour le backtesting, Telegram, TradingView et d'autres workflows avancés, démarrez une instance **OctoBot manuel** depuis la nouvelle interface OctoBot.

1. Ouvrez votre interface OctoBot node
2. Cliquez sur **New OctoBot**
3. Suivez les étapes pour démarrer une instance OctoBot manuel

<div style="text-align: center">

![Démarrer un OctoBot manuel depuis le node en cliquant sur New OctoBot](/images/guides/octobot-beta/OctoBot-node-start-manual-octobot.png)

</div>

Consultez les [guides open source](octobot) pour la configuration, les trading modes et les interfaces.

## Se connecter depuis n'importe où avec Tailscale

Si votre node tourne sur un ordinateur, un serveur ou un Raspberry Pi et que vous voulez le gérer depuis la nouvelle interface OctoBot ou l'app beta Android où que vous soyez, utilisez un réseau privé <a href="https://tailscale.com/download" rel="nofollow">Tailscale</a> plutôt que d'exposer votre node sur Internet.

Tailscale est l'un des principaux fournisseurs de réseaux privés. Le service est gratuit pour un usage personnel et repose sur un logiciel open source.

1. Téléchargez Tailscale et créez un compte Tailscale
2. Installez Tailscale sur l'ordinateur ou le serveur qui exécute votre node OctoBot
3. Installez Tailscale sur votre appareil mobile
4. Activez Tailscale sur vos deux appareils : l'app Tailscale doit afficher votre serveur et votre mobile comme **Connected**
5. Utilisez l'**adresse IP Tailscale ou MagicDNS** de votre node lors de la connexion de la nouvelle interface OctoBot

:::info
**Astuce :** Tailscale vous permet de faire tourner votre node sur n'importe quelle machine et de le piloter depuis la nouvelle interface OctoBot ou l'app beta Android sur un réseau privé sécurisé.
:::

## Dépannage de la connexion

Si vous ne parvenez pas à connecter la nouvelle interface OctoBot à votre node, vérifiez ces problèmes connus :

- Votre serveur node doit accepter les connexions entrantes. Votre réseau peut devoir être marqué comme réseau de confiance, ou votre pare-feu peut bloquer les connexions. Avec Tailscale, votre réseau Tailscale peut aussi devoir être marqué comme de confiance pour accepter les connexions.
- Votre antivirus peut aussi bloquer les connexions entrantes. Dans ce cas, essayez de le désactiver temporairement lors de la connexion à votre node. Si cela fonctionne, ajoutez l'exécutable OctoBot comme exception dans votre antivirus.

## Partager vos retours

OctoBot beta évolue activement. Vos retours nous aident à améliorer ce qui sera livré dans la version officielle.

Rejoignez-nous sur <a href="https://t.me/octobot_trading" rel="nofollow">Telegram</a> ou <a href="https://discord.com/invite/vHkcb8W" rel="nofollow">Discord</a>. Nous lisons chaque message.
