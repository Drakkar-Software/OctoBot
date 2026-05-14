---
title: "Mode de trading TradingView Signals"
description: "TradingViewSignalsTradingMode est un mode de trading configuré pour automatiser la création d'ordres sur l'exchange de votre choix en suivant les alertes de..."
keywords: ["trading modes", "strategies", "octobot", "trading-view-signals-trading-mode"]
slug: /guides/strategies/trading-modes/trading-view-signals-trading-mode
format: md
---

TradingViewSignalsTradingMode est un mode de trading configuré pour automatiser la création d'ordres sur 
l'exchange de votre choix en suivant les alertes 
d'événements de prix, d'indicateurs ou de stratégies de [TradingView](https://www.tradingview.com/?aff_id=27595).

Les alertes <a target="_blank" rel="noopener" href="https://www.octobot.cloud/en/guides/octobot-interfaces/tradingview/automating-tradingview-free-email-alerts-with-octobot?utm_source=octobot&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=TradingViewSignalsTradingModeDocs">email</a> 
gratuites de TradingView ainsi que les alertes <a target="_blank" rel="noopener" href="https://www.octobot.cloud/en/guides/octobot-interfaces/tradingview/using-a-webhook?utm_source=octobot&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=TradingViewSignalsTradingModeDocs">webhook</a>
peuvent être utilisées pour automatiser des trades basés sur les alertes TradingView.

<div class="text-center">
    <div>
    <iframe width="560" height="315" src="https://www.youtube.com/embed/HeOi4PY1ayk" 
    title="TradingView tutorial: automate any strategy with OctoBot custom automation" frameborder="0" allow="accelerometer; autoplay; 
    clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
    </div>
</div>

Pour en savoir plus, consultez le 
<a target="_blank" rel="noopener" href="https://www.octobot.cloud/en/guides/octobot-trading-modes/tradingview-trading-mode?utm_source=octobot&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=TradingViewSignalsTradingModeDocs">
guide complet du mode de trading TradingView</a>.

### Générez votre propre stratégie grâce à l'IA
Décrivez votre stratégie de trading au générateur de stratégies IA d'OctoBot et obtenez votre stratégie en Pine Script en quelques secondes.
Automatisez-la avec votre OctoBot auto-hébergé ou un <a
  href="https://app.octobot.cloud/fr/explore?category=tv&utm_source=octobot&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=tv-trading-mode-tradingview-octobot"
  target="_blank" rel="noopener">
   TradingView OctoBot</a>.
<p>
<a class="btn btn-primary waves-effect" 
  href="https://app.octobot.cloud/creator?utm_source=octobot&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=tv-trading-mode-generate-my-strategy-with-ai"
  target="_blank" rel="noopener">
   Générer ma stratégie avec l'IA
</a>
</p>

### Aide-mémoire du format d'alerte
Les signaux de base ont le format suivant :

```
EXCHANGE=BINANCE
SYMBOL=BTCUSD
SIGNAL=BUY
```

Des détails d'ordre supplémentaires peuvent être ajoutés au signal mais sont optionnels :

```
ORDER_TYPE=LIMIT
VOLUME=0.01
PRICE=42000
STOP_PRICE=25000
TAKE_PROFIT_PRICE=50000
REDUCE_ONLY=true
```

Où :
- `ORDER_TYPE` est le type d'ordre (LIMIT, MARKET ou STOP). Remplace le paramètre `Use market orders`
- `VOLUME` est le volume de l'ordre en actif de base (BTC pour BTC/USDT). Cela peut être un montant fixe (ex : `0.1` pour trader 0,1 BTC sur BTC/USD), 
un % de la valeur totale du portefeuille (ex : `2%`), un % des détentions disponibles (ex : `12a%`), un % des détentions disponibles associées aux actifs du symbole tradé actuel (`10s%`) 
ou un % des détentions disponibles associées aux actifs de toutes les paires de trading configurées (`10t%`). Il suit la <a target="_blank" rel="noopener" href="https://www.octobot.cloud/en/guides/octobot-trading-modes/order-amount-syntax?utm_source=octobot&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=TradingViewSignalsTradingModeDocs">
syntaxe des montants d'ordres</a>.
- `PRICE` est le prix de l'ordre à cours limité en actif de cotation (USDT pour BTC/USDT). Peut également être une valeur delta par rapport au prix actuel en ajoutant `d` (ex : `10d` ou `-0.55d`) ou un pourcentage delta par rapport au prix (ex : `-5%` ou `25.4%`). Il suit la <a target="_blank" rel="noopener" href="https://www.octobot.cloud/en/guides/octobot-trading-modes/order-price-syntax?utm_source=octobot&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=TradingViewSignalsTradingModeDocs">
syntaxe des prix d'ordres</a>.
- `STOP_PRICE` est le prix de l'ordre stop à créer. Peut également être un delta ou un % delta comme `PRICE`. Lors de l'augmentation de la position ou de l'achat en trading spot, le stop loss sera automatiquement créé une fois l'ordre initial exécuté. Lors de la réduction de la position (ou de la vente en spot) en utilisant un `ORDER_TYPE` LIMIT, le stop loss sera créé instantanément. *Les ordres créés de cette manière sont compatibles avec l'historique PNL.* Il suit la <a target="_blank" rel="noopener" href="https://www.octobot.cloud/en/guides/octobot-trading-modes/order-price-syntax?utm_source=octobot&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=TradingViewSignalsTradingModeDocs">
syntaxe des prix d'ordres</a>.
- `TAKE_PROFIT_PRICE` est le prix de l'ordre take profit à créer. Peut également être un delta ou un % delta comme `PRICE`. Lors de l'augmentation de la position ou de l'achat en trading spot, le take profit sera automatiquement créé une fois l'ordre initial exécuté. Lors de la réduction de la position (ou de la vente en spot) en utilisant un `ORDER_TYPE` LIMIT, le take profit sera créé instantanément. *Les ordres créés de cette manière sont compatibles avec l'historique PNL.* Il suit la <a target="_blank" rel="noopener" href="https://www.octobot.cloud/en/guides/octobot-trading-modes/order-price-syntax?utm_source=octobot&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=TradingViewSignalsTradingModeDocs">
syntaxe des prix d'ordres</a>. Les fonds seront répartis équitablement entre les take profits sauf si un `TAKE_PROFIT_VOLUME_RATIO` est défini pour chaque take profit.  
Plusieurs prix de take profit peuvent être utilisés à partir de `TAKE_PROFIT_PRICE_1`, `TAKE_PROFIT_PRICE_2`, ...
- `TAKE_PROFIT_VOLUME_RATIO` est le ratio du volume de l'ordre d'entrée à inclure dans ce take profit. Utilisé lorsque plusieurs 
take profits sont définis. Spécifiez plusieurs valeurs en utilisant `TAKE_PROFIT_VOLUME_RATIO_1`, `TAKE_PROFIT_VOLUME_RATIO_2`, .... Lorsqu'il est utilisé, un `TAKE_PROFIT_VOLUME_RATIO` est requis pour chaque take profit.  
Exemple : `TAKE_PROFIT_PRICE=1234;TAKE_PROFIT_PRICE_1=1456;TAKE_PROFIT_VOLUME_RATIO_1=1;TAKE_PROFIT_VOLUME_RATIO_2=2` répartira 33 % du montant d'entrée dans le TP 1 et 67 % dans le TP 2.
- `REDUCE_ONLY` lorsque true, ne fait que réduire la position actuelle (évite l'ouverture accidentelle d'une position short lors de la réduction d'une position long). **Utilisé uniquement en trading de futures**. La valeur par défaut est false
- `TAG` est un identifiant à attribuer aux ordres à créer.
- `LEVERAGE` la valeur de levier à utiliser lors du trading de futures.

Lorsqu'ils ne sont pas spécifiés, le volume et le prix des ordres sont automatiquement calculés en fonction du 
prix actuel de l'actif et des détentions.

Les ordres peuvent être annulés en utilisant le format suivant :
``` bash
EXCHANGE=binance
SYMBOL=ETHBTC
SIGNAL=CANCEL
```

Paramètres d'annulation supplémentaires :
- `PARAM_SIDE` est le côté des ordres à annuler ; il peut être `buy` ou `sell` pour n'annuler que les ordres d'achat ou de vente.
- `TAG` est le tag du ou des ordres à annuler. Il peut être utilisé pour n'annuler que les ordres créés avec un tag spécifique.

Note : `;` peut également être utilisé pour séparer les paramètres du signal, exemple : `EXCHANGE=binance;SYMBOL=ETHBTC;SIGNAL=CANCEL` est équivalent à l'exemple précédent.

Retrouvez le format complet des alertes TradingView dans
<a target="_blank" rel="noopener" href="https://www.octobot.cloud/en/guides/octobot-interfaces/tradingview/alert-format?utm_source=octobot&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=TradingViewSignalsTradingModeDocs">
le guide du format des alertes TradingView</a>.
