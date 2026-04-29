---
title: "TradingView"
description: "Apprenez comment automatiser vos stratégies TradingView avec OctoBot. Envoyez des alertes depuis les webhooks TradingView et tradez avec OctoBot."
sidebar_position: 4
---



# Automatiser le trading depuis TradingView

<div style="text-align: center">

![automatisation de trading tradingview illustrée par le logo tradingview](/images/guides/interfaces/tradingview-automation-illustrated-by-tradingview-logo.png)

</div>

Avec OctoBot, vous pouvez écouter les alertes <a href="https://www.tradingview.com/?aff_id=27595" rel="nofollow">TradingView</a> et automatiser vos trades en vous basant sur vos indicateurs ou stratégies TradingView.

De cette façon, quand une alerte TradingView est émise, vous pouvez instantanément créer des ordres sur la plateforme d'échange de votre choix.

Cela fonctionne avec tout type d'alerte, que ce soit:

- Un seuil de prix que vous avez défini
- Une valeur particulière atteinte par un indicateur
- Une stratégie de trading que vous utilisez sur TradingView

:::info
Ces guides concernent l'utilisation de TradingView dans le cadre des [robots de trading OctoBot](/fr/trading-bot) et <a href="https://github.com/Drakkar-Software/OctoBot" rel="nofollow">OctoBot auto-hébergé</a>. Utilisez le [guide d'investisseur trading automatisé avec TradingView](/fr/investing/tradingview-automated-trading) si vous automatisez vos stratégies TradingView avec un [OctoBot TradingView](/fr/investing/tradingview-trading-tutorial) depuis [www.octobot.cloud](https://www.octobot.cloud/fr).
:::

Pour en apprendre plus sur l'automatisation de stratégies TradingView dans OctoBot, rendez-vous sur le [guide du Trading Mode TradingView](/guides/octobot-trading-modes/tradingview-trading-mode)

## Alertes basées sur un indicateur

Votre OctoBot peut trader en se basant sur des indicateurs TradingView ou des évènements de prix. Suivez le [guide des alertes d'indicateur](tradingview/automating-trading-from-an-indicator) pour en savoir plus.

## Alertes basées sur une stratégie

Vous pouvez aussi faire en sorte que votre Octobot trade selon une stratégie Trading écrite en Pine Script. Pour cela, suivez le [guide des alertes de stratégies](tradingview/automating-trading-from-a-pine-script-strategy) pour synchroniser votre OctoBot avec votre stratégie TradingView.

## Configuration d'OctoBot

Ajoutez simplement l'interface `Trading-view` à la configuration "Accounts" de votre OctoBot et configurez le [service de webhook](tradingview/using-a-webhook).

## Compte TradingView

Tout d'abord, créez un compte <a href="https://www.tradingview.com/?aff_id=27595" rel="nofollow">TradingView</a> si vous n'en avez pas déjà un.

Ensuite, pour pouvoir automatiser votre stratégie TradingView, vous aurez besoin d'utiliser des [webhooks](tradingview/using-a-webhook), ce qui nécessite un compte TradingView pro. Si vous n'en avez pas, vous pouvez utiliser l'essai gratuit de 30 jours.

<div style="text-align: center">

<a href="https://www.tradingview.com/?aff_id=27595" rel="nofollow">![bouton plan pro tradingview](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/tradingview-go-pro-trial-button.png)</a>

</div>

<div style="text-align: center">

![tradingview démarrer essai gratuit](https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/tradingview-start-trial-button.png)

</div>


Votre compte est maintenant prêt à être utilisé avec OctoBot !

## Format des alerte

Vous pouvez envoyer des commandes à votre OctoBot en utilisant des alertes TradingView, y compris la création d'ordres au marché ou aux limite, la prise de bénéfices, l'annulation d'ordres et bien plus encore.

Consultez le [guide de format d'alerte](tradingview/alert-format) pour en savoir plus.
