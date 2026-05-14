---
title: "Changelog"
description: "Historique des versions et changelog d'OctoBot. Suivez les nouvelles fonctionnalités, améliorations et corrections de bugs."
keywords: ["changelog", "releases", "octobot", "updates", "version history"]
slug: /developers/changelog
sidebar_position: 91
format: md
---

# Changelog
Toutes les modifications notables apportées à ce projet seront documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

*Il est fortement conseillé d'effectuer une mise à jour de vos tentacles après avoir mis à jour OctoBot. (start.py tentacles --install --all)*

## [2.1.1] - 2026-03-28
### Ajouté
- [GridTrading] Ajout de l'option de configuration reinvest_profits
- [DSLTradingMode] Ajout du DSLTradingMode
### Modifié
- [CCXT] Mise à jour vers ccxt 4.5.44
- [Exchanges]: Amélioration du cache du statut de marché des exchanges
- [Polymarket]: Amélioration de la récupération des tickers
### Corrigé
- [Hyperliquid]: Correction de la valorisation des actifs et des problèmes liés au websocket
- [WebInterface]: Correction de l'affichage des paramètres GPT
- [Webinterface]: Amélioration des vérifications de redirection. Remerciements particuliers à zhangqy24

## [2.1.0] - 2026-03-17
### Mise à jour de la version de Python
**OctoBot fonctionne désormais sur Python 3.13 et 3.12. Les versions 3.10 et 3.11 ne sont plus prises en charge**
### Changement de structure des dépôts
L'intégralité du code d'OctoBot se trouve désormais dans le dépôt https://github.com/Drakkar-Software/OctoBot, toutes les dépendances d'OctoBot ayant été migrées dans le dossier packages de ce dépôt.
### Ajouté
- [Polymarket] [Beta] Prise en charge de Polymarket. Distribution dédiée sur https://github.com/Drakkar-Software/OctoBot-Prediction-Market
- [ProfileCopyTradingMode] Ajout d'un trading mode pour copier un profil de trading public, actuellement utilisé pour le copy trading sur polymarket
- [LBank] Ajout de la prise en charge de l'exchange LBank
### Corrigé
- [Coinex]: Correction du parsing des ordres maker only

### Développement en cours, Beta bientôt disponible
- [AI Agents] Prise en charge du trading et du backtesting par agents IA. Distribution dédiée sur https://github.com/Drakkar-Software/OctoBot-AI

### À venir
Cette version est la première étape vers un tout nouveau type d'OctoBot sur lequel nous travaillons actuellement. Ce nouveau type de bot apportera plus de possibilités et de flexibilité que jamais pour rendre simple l'automatisation de n'importe quelle action ou stratégie sur vos investissements en crypto.
Plus d'informations bientôt.

## [2.0.16] - 2025-12-24
### Ajouté
- [Automations] ajout d'une condition d'automatisation scriptée utilisant le DSL d'OctoBot
- [DSL] ajout du mot-clé portfolio holding
- [DSL] ajout de la documentation web
### Modifié
- [Exchanges] mise à jour vers ccxt 4.5.28
- [HollaEx] rend les paliers de frais configurables
### Corrigé
- [Binance]: Correction des ordres stop futures
- [HollaEx]: correction de l'erreur de frais manquants
- [Hyperliquid] correction du démarrage du websocket


## [2.0.15] - 2025-12-08
### Changement majeur de l'installation pip
Pour installer l'OctoBot complet (équivalent aux versions précédentes), OctoBot doit être installé avec le paramètre [full] : `pip install octobot[full]`
### Ajouté
- [TradingModes] ajout de politiques d'annulation
- [DSL] ajout des tentacles DSL et de mots-clés de base
### Modifié
- Installation légère : OctoBot peut désormais être utilisé avec des dépendances minimales lorsqu'il est démarré avec la variable d'environnement USE_MINIMAL_LIBS=true
- Installation complète : pour utiliser l'OctoBot complet (avec interface utilisateur, etc.), installez octobot[full]
- [Exchanges] mise à jour vers ccxt 4.5.22
- [Hyperliquid] correction de la récupération des marchés et utilisation de tickers uniformes
- Typage : ajout du typage à la plupart des objets d'OctoBot-Trading
- [TradingView] dépréciation des alertes par e-mail
### Corrigé
- [RaspberryPi]: Correction du crash "Illegal instruction"
- [Exchanges] correction de l'erreur de proxy lors du chargement des marchés
- [StaggeredOrders] correction d'une erreur d'ordres rare

## [2.0.14] - 2025-10-29
### Corrigé
- Rendu la dépendance pyarrow optionnelle pour empêcher une rare erreur d'import de .dll
- [Coinbase] correction de l'erreur de chargement des marchés lorsque les clés API sont invalides
- [IndexTrading] correction des problèmes de déclenchement concurrent
- [WebInterface] correction d'un problème de latence de l'UI lors de la configuration du profil

## [2.0.13] - 2025-10-17
### Ajouté
- [GridTrading] Système de trailing ordre par ordre
- [Exchanges] Prise en charge de myokx et okxus
- [Binance] Prise en charge du demo trading sur Binance futures
- [Coinbase] Prise en charge du format de clés API Ed25519
- [Coinbase] Prise en charge des websockets
- [Hyperliquid] Journalisation des paires de trading disponibles au démarrage
- [Exchanges] Ajout d'un système d'auto-retry sur des erreurs de requêtes spécifiques aux exchanges
- [Exchanges] Ajout d'un système d'autofix des tickers
- [Scripting] Ajout de mots-clés Backtesting & data collector
- [IndexTrading] Ajout de politiques de synchronisation
- [Infra] Ajout d'octobot.hcl
### Modifié
- [TradingView] Rend les erreurs de configuration et de signal beaucoup plus visibles
- [CCXT] Mise à jour vers CCXT 4.5.8
- [Orders] Gère correctement les ordres partiellement exécutés
- [Orders] L'ajout des poussières aux ordres de vente peut désormais être désactivé à l'aide de la variable d'environnement INCLUDE_DUSTS_IN_SELL_ORDERS_WHEN_POSSIBLE
- [Exchanges] Amélioration de la précision des erreurs
- [Coinbase] Utilisation du niveau de frais intro 2 par défaut
- [WebInterface] Affichage du lien de paiement en repli lorsque nécessaire
- [WebInterface] Mise en cache de la vérification de version pour réduire les requêtes
- [OpenAI] Correction des dépréciations et prise en charge des modèles les plus récents
- [Exchanges] Rend l'erreur "too many open orders" plus claire
### Corrigé
- [MEXC] Correction des problèmes de websocket
- [Kucoin] Correction des problèmes de parsing
- [Orders] Correction d'une erreur de frais liée aux ordres au marché
- [GridTrading] Correction d'une tarification incorrecte des ordres
- [GridTrading] Correction d'une réinitialisation incorrecte des ordres
- [WebInterface] Correction des liens cassés
- [TradingModes] Correction d'une rare erreur d'arrêt prématuré du backtesting

## [2.0.12] - 2025-06-09
### Modifié
- [WebInterface] Restauration de la configuration de la quantité d'ordre du trading mode (vraiment, cette fois)
- [Community] Rend l'erreur d'authentification plus spécifique
- [HollaEx] Prise en charge des ordres stop, frais précis des exchanges basés sur HollaEx et problèmes de liste blanche d'IP
- [Exchanges] Augmentation du nombre d'ordres ouverts par défaut à 100
### Corrigé
- [HollaEx] Correction des problèmes de signature et de récupération des bougies

## [2.0.11] - 2025-06-06
### Ajouté
- [DCATradingMode] Gestion du nombre maximum d'ordres ouverts par exchange
- [Backtesting] Prise en charge du backtesting des exchanges HollaEx avec les règles de marché réelles
### Modifié
- [DCATradingMode] Met désormais à jour le levier avant d'entrer dans une nouvelle position en trading de futures lorsque le levier est différent de celui configuré
- [DCATradingMode] Amélioration du message d'erreur "missing funds" pour le rendre plus facile à comprendre et à corriger
- [WebInterface] Suppression de la configuration "emit signals" du trading mode
### Corrigé
- [WebInterface] Correction de l'affichage incorrect du PNL dans la vue PNL
- [WebInterface] Restauration de la configuration de la quantité d'ordre du trading mode
- [Kucoin] Correction des problèmes lors du réglage du levier des positions cross
- [Exchanges] Problèmes de stop loss et d'édition d'ordres
- [Exchanges] Rares problèmes de synchronisation d'annulation d'ordres

## [2.0.10] - 2025-05-21
### Ajouté
- [Distributions] Ajout de la [distribution de market making](https://github.com/Drakkar-Software/OctoBot-Market-Making)
- [Orders] Prise en charge des ordres stop et take profit simultanés en trading spot grâce au nouveau système d'ordres inactifs. Ceci est utilisé par défaut lorsque des stop losses sont créés aux côtés de take profits en trading réel.
- [TradingViewTradingMode] Prise en charge de volumes personnalisés lors de l'utilisation de plusieurs take profits
- [Exchanges] Ajout de Hyperliquid
### Modifié
- [CCXT] mise à jour vers CCXT 4.4.85
- [DCATradingMode] Simplification du sélecteur de stratégie
- [IndexTradingMode] Annule désormais les ordres ouverts au démarrage du rééquilibrage afin de libérer des fonds pour le rééquilibrage
- [TradingViewTradingMode] Journalise désormais toutes les requêtes au niveau info pour les afficher par défaut dans le terminal
- [Bitfinex] Renommage de bitfinex2 en bitfinex
- [WavesExchanges] Correction des problèmes de parsing du statut de marché
### Corrigé
- [Orders] Correction d'un rare problème de calcul de frais provoquant l'échec du rééquilibrage du trading mode Index
- [FuturesTrading] Correction des problèmes d'ordres d'inversion de position
- [WebInterface] correction de l'affichage du portefeuille historique multi-exchanges
- [Staggered & Grid trading modes] Correction des problèmes d'affichage du PNL
- [Staggered & Grid trading modes] Amélioration du message d'erreur des ordres interférents pour le rendre plus facile à comprendre
- [DCATradingMode] Correction des montants des ordres secondaires lors du trading de futures
- [Daily & TradingView trading modes] Correction des problèmes de configuration des ordres "all in"
### Note pour les utilisateurs de Bybit
Nous n'avons pas eu le temps d'inclure la correction du compte unifié Bybit dans cette version. Nous la
programmons pour la prochaine.

## [2.0.9] - 2025-03-06
### Ajouté
- [Community] Prise en charge des stratégies créées par OctoBot AI
- [EMAMomentumEvaluator] Ajout du paramètre "reverse_signal" à la configuration
- [Exchanges] Gestion de l'erreur de liste blanche d'IP
- [Exchanges] Gestion des proxies socks
### Modifié
- [Trades] Journalisation de plus d'informations sur les trades historiques chargés
- [Orders] Amélioration de l'erreur de montant d'ordre invalide
- [Coinbase] Ignore les paires de trading aliasées non négociables (telles que BTC/USD)
- [TradingModes] N'interrompt pas l'exécution en cas d'échec de l'annulation des ordres
- [TradingModes] Amélioration de la gestion des frais des ordres chaînés : ne compte que les frais de l'ordre initial dans le dernier ordre chaîné créé
- [GridTrading] Ajout d'un avertissement lorsque le trailing est ignoré à cause de la configuration des ordres cibles
### Corrigé
- [Community] Correction de l'inscription à www.octobot.cloud depuis OctoBot
- [Exchanges] Correction des problèmes d'authentification lors de l'utilisation d'exchanges en lecture seule
- [Orders] Correction des problèmes de synchronisation des ordres stop
- [Backtesting] Correction d'un problème de timeout lors de l'initialisation des prix
- [TradingModes] Correction des problèmes de prix manquant lors des inits DCA et Grid
- [IndexTrading] Correction du backtesting lorsqu'aucune configuration historique n'est fournie
- [GPTEvaluator] Affichage du sélecteur de modèle même lorsqu'un seul modèle est disponible
- [CoinEx] Correction du parsing des ordres partiellement exécutés
- [Binance.us] Correction du calcul des frais
- [Configuration] Autorisation des cryptos à un seul caractère (telles que "S")

## [2.0.8] - 2025-01-27
### Ajouté
- [Profiles] Profil par défaut trailing grid
- [GridTrading] Options de trading à la hausse et à la baisse
- [TradingView] Prise en charge du paramètre LEVERAGE pour mettre à jour la valeur du levier de la position
- [TradingView] Envoi du paramètre REDUCE_ONLY aux ordres des exchanges
- [Exchanges] Prise en charge des stop losses au marché spot côté exchange pour Binance, Coinbase, Kucoin et BingX
- [Exchanges] Ajout de la prise en charge des proxies http, https et ws
- [Exchanges] Ajout d'un compteur de requêtes http
- [Exchanges] Ajout d'un compteur de requêtes
- [Exchanges] Ajout de la prise en charge de domaines d'exchange personnalisés
- [WebInterface] Ajout d'une indication d'absence d'exchange activé en cas de problème de configuration
### Modifié
- [GPTService] Amélioration de la documentation des LLM personnalisés
- [GPTService] Prise en charge d'un token vide lors de l'appel de LLM personnalisés
- [Orders] Rend les ordres chaînés plus fiables
- [Exchanges] Réduction de la taille des logs pour les erreurs de contenu html
### Corrigé
- [FuturesTrading] Correction des problèmes de synchronisation des positions
- [TradingModes] Correction de rares problèmes de création d'ordres de vente
- [GridTrading & StaggeredOrders] Correction de nombreux problèmes de quantité et de prix en live et en backtesting
- [DCATradingMode] Correction d'un rare problème d'init
- [MarketPrice] Correction d'un problème de mark price
- [Backtesting] Correction des problèmes de backtesting du trading de futures
- [MEXC] Nombreuses corrections
- [BingX] Corrections d'ordres
- [Exchanges] Correction d'un rare parsing incorrect des ordres stop
- [Exchanges] Correction de rares erreurs d'annulation d'ordres
- [Exchanges] Correction de rares problèmes de spam de requêtes d'exchange sur des erreurs en boucle
- [Community] Correction de l'erreur de session expirée
- [Community] Correction de l'erreur de la page /community
- [Community] Correction des problèmes liés au SSL

## [2.0.7] - 2024-10-26
### Ajouté
- [TradingView] Prise en charge de plusieurs take profits
- [TradingView] Prise en charge de ";" comme séparateur de paramètres
- [GPTService] Prise en charge d'une base_url personnalisée pour utiliser d'autres LLM que ceux d'OpenAI
- [Exchanges] Prise en charge des proxies http et https
### Modifié
- [TradingView] Mise à jour de la documentation de l'interface web
### Corrigé
- [Exchanges] Boucle d'erreur d'authentification
- [WebInterface] Correction de l'affichage du code markdown en mode sombre

## [2.0.6] - 2024-10-08
### Ajouté
- [TradingView] Prise en charge des alertes TradingView par e-mail
### Modifié
- [TradingView] Amélioration de l'affichage du webhook
- [WebInterface] Amélioration du compte
- [HollaEx] Amélioration de la prise en charge globale
### Corrigé
- [Orders] Correction des problèmes de synchronisation
- [Storage] Correction des problèmes de stockage des ordres
- [Exchanges] Nouvelle tentative de récupération du statut de marché en cas d'échec pour timeout
- [Credentials] Gestion des identifiants d'exchange avec espaces et sauts de ligne en début/fin
- [Extension] Correction des problèmes de vérification de l'extension et de session de paiement
- [Exchanges] Correction d'une rare interprétation erronée de l'erreur de clé invalide
- [WebInterface] Correction des problèmes de performance de l'interface web liés aux notifications
- [WebInterface] Correction des problèmes de performance de fetch_upgrade_version
- [Evaluators] Suppression d'un avertissement non pertinent lors de la mise à jour globale des évaluateurs temps réel

## [2.0.5] - 2024-08-27
### Corrigé
- [Portfolio] Correction des problèmes de ZeroDivisionError
- [Grid] Correction des problèmes d'affichage de l'intervalle d'auto-dispatch
- [Evaluators] Journalisation d'un avertissement lors de la transmission d'une évaluation obsolète

## [2.0.4] - 2024-08-25
### Ajouté
- [BitMart] L'exchange BitMart est désormais officiellement pris en charge
- [GridTrading] Configuration du délai de redistribution des fonds
### Modifié
- [WebInterface] Amélioration de l'affichage de l'historique du portefeuille et plus de flexibilité
- [Webhook] Rend les messages d'erreur plus faciles à comprendre
- [CCXT] mise à jour vers ccxt 4.3.85
- [Community] Correction des problèmes liés à l'authentification community
### Corrigé
- [GridTrading] Correction des problèmes de réinitialisation de la grille lorsque la redistribution des fonds est activée
- [MEXC] Correction des problèmes de récupération des paires négociées sur MEXC
- [OKX] Correction des problèmes de parsing du levier
- [WebInterface] Correction des problèmes d'UI d'annulation d'ordres
- [Configuration] Correction des problèmes liés au fichier de récupération

## [2.0.3] - 2024-08-03
### Ajouté
- [IndexTradingMode]: Profil par défaut, intraday, option de mise à jour en temps réel et contenu personnalisé
### Modifié
- [Trades] Augmentation importante du nombre maximum de trades dans l'historique
- [Updaters] Restauration de l'updater binaire
- [WebInterface] Amélioration de l'affichage des chandeliers
- [WebInterface] Amélioration de l'UI du thème sombre
### Corrigé
- [WebInterface] Ignore les bots archivés dans l'onglet community
- [Kucoin] Problèmes de websocket lors de l'utilisation de plus de 100 feeds
- [Notifications] Affiche désormais le PNL réel des trades ou aucun PNL du tout

## [2.0.2] - 2024-07-17
### Modifié
- [WebInterface] Amélioration de l'affichage des thèmes clair et sombre
### Corrigé
- [WebInterface] Correction du paiement de l'extension
- [RAM] Réduction de la RAM requise lors du chargement d'un grand nombre de trades
- [BingX] Correction des problèmes de dimensionnement des ordres

## [2.0.1] - 2024-07-09
### Modifié
- [WebInterface] Ajout du contact sur la page de l'extension
- [WebInterface] amélioration de l'affichage
### Corrigé
- [WebInterface] problèmes d'affichage

## [2.0.0] - 2024-07-05
### Ajouté
- [Extension]: Nouvelle extension OctoBot pour profiter du Strategy designer, sécuriser les webhooks TradingView et bénéficier de paniers de cryptos automatiquement mis à jour
- [WebInterface] Mode clair et sombre
- [Webhook] Prise en charge des webhooks propulsés par OctoBot cloud comme alternative à ngrok
### Modifié
- [WebInterface] Refonte complète de l'UI
- [CCXT] mise à jour vers ccxt 4.3.56
### Corrigé
- [Coinbase] problème de rate limit
- [Exchanges] problèmes de vérification des permissions
- [Orders] correction des problèmes de nouvelle tentative de requêtes

## [1.0.10] - 2024-04-19
### Corrigé
- [Tentacles download] Correction d'un rare problème lié aux certificats SSL lors du téléchargement des tentacles
- [DeathAndGoldenCrossEvaluator] Ne se déclenche désormais que juste après les croisements

## [1.0.9] - 2024-04-18
### Ajouté
- [DigitalOcean] Ajouté à la marketplace et gestion du déploiement en un clic
- [IndexTradingMode] Ajout du trading mode Index permettant de suivre des index personnalisés
- [TradingViewTradingMode] Ajout du quote et des offsets par rapport au prix actuel
- [DCATradingMode] Ajout du ratio de détention maximum pour plafonner l'exposition maximale à un actif
- [Coinbase] Gestion du nouveau format de clé API
### Modifié
- [CCXT] Mise à jour vers CCXT 4.2.95
### Corrigé
- [ChainedOrders] Correction du calcul de la quantité des ordres chaînés lors de la gestion des frais
- [ChainedOrders] Correction du prix d'exécution en backtesting des ordres chaînés pour s'adapter aux bougies actuelles
- [StopLoss] Recrée désormais toujours les stop losses au redémarrage en trading réel
- [Orders] Correction de rares problèmes de création d'ordres
- [Coinbase] Correction des problèmes de récupération des ordres
- [BinanceUS] Correction des vérifications de permissions
- [Kucoin] Correction d'un rare problème de création d'ordre
- [MEXC] Correction des problèmes d'annulation d'ordres
- [WebInterface] Ajout de robots.txt pour empêcher l'indexation par les moteurs de recherche

## [1.0.8] - 2024-02-14
### Ajouté
- [TradingView] Prise en charge des stop loss autonomes et des tags d'ordres
### Modifié
- [Tentacles] Amélioration de la documentation
- [WebInterface] Correction de la vérification des identifiants d'exchange lors de l'utilisation de comptes futures
- [Exchanges] Augmentation du nombre maximum de bougies de base et possibilité de le personnaliser via une variable d'environnement
- [Links] liens octobot.cloud
### Corrigé
- [Exchanges] Suppression du spam de logs sur les identifiants invalides
- [Cloud strategies] Correction du téléchargement des stratégies cloud

## [1.0.7] - 2024-01-18
### Ajouté
- [CoinEx] Prise en charge de CoinEx
### Modifié
- [WebInterface] Affichage de la rentabilité même en cas d'erreur de backtesting, remerciements particuliers à Phodia pour cette amélioration.
### Corrigé
- [Exchanges] Problèmes de reconnexion du websocket
- [DailyTradingMode] Correction du montant de vente lors d'un short en mode Target Profits

## [1.0.6] - 2024-01-09
### Ajouté
- [TradingModes] Amélioration de la documentation et ajout de liens vers les guides complets
- [InstantMAEvaluator] Ajout d'un seuil de déclenchement pour éviter de se déclencher à chaque mise à jour de prix
### Modifié
- [CCXT] mise à jour vers ccxt 4.2.10
- [ChatGPT] mise à jour vers openai 1.7.0
- [DailyTradingMode] Activation de l'augmentation de position en futures : ajout d'un avertissement
### Corrigé
- [DailyTradingMode] gestion d'un MAX_CURRENCY_RATIO invalide
- [TradingView] Correction d'une faute de frappe dans la documentation SIGNAL=CANCEL
- [Exchanges] Problèmes de synchronisation des ordres MEXC
- [Exchanges] HTX a renommé Huobi en HTX
### Supprimé
- [Exchanges] Bittrex

## [1.0.5] - 2023-12-19
### Ajouté
- [GPTEvaluator] Paramètres pour limiter les tokens utilisés et désactiver la ré-évaluation
### Modifié
- [WebInterface] Amélioration de l'affichage de l'accueil sur les écrans plus petits
### Corrigé
- [Telegram] Correction de plusieurs problèmes de commandes telegram
- [TradingViewSignalsTradingMode] Correction des problèmes de quantité des ordres d'achat
- [WebInterface] Correction des problèmes de logs
- [GoogleTrends] Correction des problèmes avec les cryptos en plusieurs mots
- [Exchanges] Rare erreur de récupération des bougies

## [1.0.4] - 2023-12-10
### Ajouté
- [Strategies] Les stratégies cloud d'OctoBot peuvent désormais être téléchargées et utilisées comme des profils OctoBot classiques
- [DailyTradingMode] Nouveau paramètre "Enable futures position increase" pour éviter de construire sur des positions existantes lors du trading de futures
- [DCATradingMode] Nouveau paramètre "Health check" pour s'assurer qu'aucun fonds ne reste invendu lors de l'utilisation de take profits
- [Exchanges] Prise en charge du trading spot sur Bingx
### Modifié
- [CCXT] vers la version 4.1.82
- [WebInterface] Amélioration de la vitesse de chargement de /profile
### Corrigé
- [WebInterface] Correction de la liste de devises obsolète dans /profile
- [Ngrok] Correction d'un problème de configuration lié aux domaines personnalisés
- [Exchanges] Correction des problèmes de stop loss et de take profit
- [Orders & Trading Modes] Plusieurs erreurs rares

## [1.0.3] - 2023-10-30
### Corrigé
- [Exchanges] problème de time frame en temps réel

## [1.0.2] - 2023-10-29
### Ajouté
- [ChatGPT] Backtesting sur les configurations prises en charge, liste complète sur https://www.octobot.cloud/features/chatgpt-trading
- [TradingView] Prise en charge du signal d'annulation d'ordres
- [GridTrading] Optimisation de la commande de portefeuille initial pour répartir les fonds de manière optimisée avant de démarrer le trading mode
- [DCATrading] Option de ne pas annuler les ordres précédemment créés
- [DCATrading] Option de toujours créer les ordres initiaux au démarrage en mode évaluateurs
- [Webhook] Prise en charge des domaines personnalisés Ngrok
### Modifié
- [ChatGPT] Le profil GPT Trading par défaut utilise désormais le trading mode DCA
- [TradingView] Refonte de la documentation sur https://www.octobot.cloud/en/guides/octobot-interfaces/tradingview
- [DCATrading] Amélioration des messages d'erreur
- [WebInterface] Ne sélectionne pas les profils dupliqués par défaut
- [DataCollector] Rend les erreurs plus claires
- [Links] Migration vers https://www.octobot.cloud/
### Corrigé
- [Kucoin] Problème concernant les tailles d'ordre minimales
- [Backtesting] Problème sur les ordres pouvant être exécutés sur la même bougie où ils ont été créés
- [DCATrading] Problèmes de déclencheur basé sur le temps
- [Grid & Staggered orders] Correction de la création d'ordres lorsqu'on est proche du spread

## [1.0.1] - 2023-09-28
### Corrigé
- [Community] Erreur de timeout de connexion au compte OctoBot

## [1.0.0] - 2023-09-26
### Modifié
- [Community] Migration vers le octobot.cloud mis à jour. Détails complets sur https://www.octobot.cloud/en/blog/introducing-the-new-octobot-cloud
- [Logs] Amélioration des logs de debug
### Corrigé
- [GridTrading] Problèmes de rééquilibrage des ordres miroirs
- [DCA & Dip Analyser] Problèmes de division des ordres de vente

## [0.4.54] - 2023-08-31
### Ajouté
- [Kucoin] Vérifications des permissions de clé API
- [OKX] Vérifications des permissions de clé API
### Modifié
- [GridTrading] Amélioration du calcul de la quantité à l'aide des trades récents
- [Orders] Affichage de l'erreur de permission lorsque les permissions de trading manquent dans la clé API
- [TradingView] Documentation de la quantité
- [Logging] Réduction des logs des requêtes httpx
### Corrigé
- [TradingView] Erreur de webhook
### Supprimé
- [Python] Suppression de la prise en charge de la 3.9. La 3.10 est désormais la version de Python requise

## [0.4.53] - 2023-08-22
### Ajouté
- [Smart DCA] Refonte du trading mode DCA pour gérer les évaluateurs, les entrées et sorties échelonnées
- [GridTrading] Prise en charge de la réallocation des fonds
- [TradingModes] Types de quantité s% et t% pour trader un % des actifs négociés du portefeuille
- [WebInterface] Historique des notifications
- [WebInterface] Conseils avancés
- [BingX] Simulateur de trading
### Modifié
- [WebInterface] Vérifie désormais la permission de trading lors de l'ajout de clés d'exchange
### Corrigé
- [WebInterface] Problèmes d'affichage des ordres
- [WebInterface] Problèmes d'import des devises
- [Binance] Correction de l'API futures
- [Kucoin] Correction de l'API et du websocket
- [Orders] Restauration des ordres chaînés
- [Backtesting] Correction du calcul des frais sur les très petits trades
- [Storage] Correction des problèmes de fichier corrompu

## [0.4.52] - 2023-07-05
### Ajouté
- [Exchanges] Prise en charge de Binance futures
- [Exchanges] Crypto.com, Kucoin et MEXC en tant qu'exchanges partenaires
- [Orders] Prise en charge complète des stop loss sur les exchanges de futures
### Modifié
- [Futures] Amélioration des messages d'erreur liés au trading de futures
- [WebInterface] amélioration des conseils de configuration
### Corrigé
- [Futures] Problèmes de synchronisation des positions de trading de futures
- [Orders] Problèmes liés aux signaux de trading
- [Evaluators] Problèmes de time frames liés à la configuration

## [0.4.51] - 2023-06-09
### Modifié
- [WebInterface] amélioration du statut de marché
- [WebInterface] ajout de conseils de configuration
### Corrigé
- [Orders] problèmes de synchronisation des ordres
- [Display] affichage de la configuration des tentacles
- [Display] affichage lié aux time frames

## [0.4.50] - 2023-05-06
### Ajouté
- [DailyTradingMode] Mode Target profit
- [ArbitrageTradingMode] Possibilité de désactiver les arbitrages short ou long
- [WebInterface] Tableau des trades de backtesting
- [WebInterface] Affichage des ordres ouverts sur les graphiques
- [WebInterface] Sélecteur de time frame sur les graphiques
- [Python] Prise en charge de la 3.9 et de la 3.10. La 3.10 est désormais la version recommandée pour OctoBot
### Modifié
- Suppression de Cython
- Amélioration de la vitesse globale grâce aux optimisations de python 3.10
- [Trading Modes] autorisation de la quantité d'ordre en montant quote
- [Coinbase] Correction des problèmes du simulateur de trading
- [Bybit] Rend les erreurs de synchronisation horaire beaucoup moins fréquentes
- [WebInterface] Amélioration du sélecteur de symboles spot et futures
- [Websockets] Amélioration de la stabilité globale
### Corrigé
- [Websockets] KeyError
- [Portfolio] Erreur d'attribut

## [0.4.49] - 2023-04-23
### Modifié
- [CCXT] Mise à jour vers ccxt 3.0.74
- [Websockets] Réduction des avertissements de bougies non ordonnées
### Corrigé
- [Coinbase] Mode simulateur de trading et data collector
- [Binance] Problèmes de création d'ordres
- [Bybit] Problèmes de création d'ordres
- [Telegram] commande set risk
- [TradingView] suppression de l'avertissement sur les lignes vides

## [0.4.48] - 2023-04-18
### Ajouté
- [WebInterface] Ajout de filtres à l'onglet PNL.
- [TradingViewTradingMode] Gestion du take profit et du stop loss à l'ouverture de position.
- [DCATradingMode] Ajout de la configuration du prix et du type d'ordre.
- [Hollaex] Possibilité de désactiver le websocket sur les exchanges Hollaex.
### Modifié
- [Telegram] Amélioration de l'affichage du portefeuille. Remerciements particuliers à Tim !
- [Websockets] Gestion des time frames partiellement prises en charge
- [Trading Modes] Amélioration des messages d'erreur de création impossible
- [WebInterface] Affichage des graphiques sur mobile.
### Corrigé
- [Websockets] spam de logs
- [Databases] Gestion des formats de fichiers de bdd incorrects
- [PNL] problèmes liés au PNL des trades invalides
- [WebInterface] Affichage du portefeuille sur les écrans plus petits.

## [0.4.47] - 2023-04-02
### Ajouté
- [Evaluators] Évaluateur ChatGPT
- [Exchanges] Restauration de la prise en charge de Coinbase
- [Profiles] Risque et complexité
### Modifié
- [WebInterface] Amélioration de l'affichage des graphiques en bougies. Remerciements particuliers à Tim !
- [Services] Versions des connecteurs Telegram, flask, reddit et autres
### Corrigé
- [OKX] problèmes de création d'ordre
- [WebInterface] Correction des déconnexions client inattendues
- [PNL] problèmes liés au PNL des trades invalides


## [0.4.46] - 2023-03-24
### Modifié
- [Telegram] affichage du portefeuille
### Corrigé
- [Orders] problème de chargement des ordres sauvegardés

## [0.4.45] - 2023-03-23
### Ajouté
- [Trades] valeur dans le marché de référence
- [PNL] frais détaillés
### Modifié
- [Telegram] augmentation du délai de timeout
- [Telegram] avoirs du portefeuille du bot dans le marché de référence (merci, @Max)
### Corrigé
- [Orders] problèmes des ordres initialement récupérés

## [0.4.44] - 2023-03-20
### Corrigé
- [Community] problèmes de mise à jour du portefeuille
- [OrderStorage] problèmes de typage

## [0.4.43] - 2023-03-19
### Corrigé
- [Profiles] gestion des erreurs de mise à jour des profils
- [Portfolio] problèmes de valorisation du portefeuille d'origine

## [0.4.42] - 2023-03-18
### Ajouté
- Prise en charge du trading spot sur Crypto.com
- Prise en charge du trading spot sur Bybit
- Stockage des ordres : en trading réel, les stop loss, tags, groupes et ordres chaînés sont sauvegardés entre les sessions
### Modifié
- Amélioration de la valorisation du portefeuille
- Amélioration de l'affichage du PNL
- Bibliothèque Telegram passée en version asynchrone pour de meilleures performances
### Corrigé
- PNL en trading réel
- Calcul de la limite de prix lors de la création d'ordre

## [0.4.41] - 2023-03-03
### Ajouté
- Historique du PNL des trades pour les trading modes pris en charge
- Prise en charge des futures OKX
- Prise en charge des ordres au marché dans Dip Analyser
### Modifié
- Refonte de l'onglet trading de l'interface web
- Réduction de la RAM requise pour les instances longue durée
- Optimisation des opérations de lecture/écriture sur disque lors de la navigation dans l'interface web
### Corrigé
- Problèmes de synchronisation et d'annulation des ordres
- Problèmes de synchronisation des positions de trading de futures
- Problèmes de création d'ordre liés aux montants minimum et maximum des ordres

## [0.4.40] - 2023-02-17
### Corrigé
- Réinitialisation du portefeuille historique

## [0.4.39] - 2023-02-14
### Corrigé
- Problèmes de portefeuille historique et de métadonnées live

## [0.4.38] - 2023-02-12
### Ajouté
- Historique des trades et du portefeuille à travers les sessions OctoBot
- Configuration par défaut du grid trading pour n'importe quelle paire
### Corrigé
- Problèmes de rate limit Kucoin
- Problèmes de synchronisation du portefeuille
- Daily trading : ne place un stop loss que lors de la réduction de la taille de la position

## [0.4.37] - 2023-02-06
### Ajouté
- Configurations : ajout de limites
### Corrigé
- Trading de futures : problèmes de portefeuille et d'annulation d'ordres

## [0.4.36] - 2023-01-29
### Ajouté
- Automations : initialisation des automatisations
- Dip Analayser : ajout de l'option stop loss
### Corrigé
- Websockets : problèmes de reconnexion

## [0.4.35] - 2023-01-19
### Ajouté
- WebInterface : formulaire d'inscription à OctoBot cloud
### Modifié
- Websockets : version de ccxt
### Corrigé
- Websockets : erreur de kline

## [0.4.34] - 2023-01-14
### Ajouté
- Websockets : prise en charge de bien plus de feeds et d'exchanges
### Modifié
- Websockets : migration de cryptofeed vers ccxt pro
- Vitesse d'affichage de l'interface web
- Affichage des logos des coins
- Affichage mobile

## [0.4.33] - 2023-01-02
### Ajouté
- Sélecteur de profil
- Persistance de la session de connexion
### Modifié
- Tutoriels
- Affichage mobile

## [0.4.32] - 2022-12-29
### Corrigé
- Problèmes de reconnexion MQTT

## [0.4.31] - 2022-12-28
### Corrigé
- téléchargement en double du profil
- problème de typage d'octobot trading

## [0.4.30] - 2022-12-27
### Corrigé
- erreur de téléchargement du profil

## [0.4.29] - 2022-12-26
### Corrigé
- installation pip sur Unix
- crash sur configuration de setup des tentacles de profil manquante

## [0.4.28] - 2022-12-25
### Ajouté
- Tentacles de mots-clés
- Prérequis d'OctoBot-Pro
- Variable d'environnement de désactivation du Clock Synchronizer : ENABLE_CLOCK_SYNCH=False
### Corrigé
- Problèmes du tableau de bord multi-exchanges

## [0.4.27] - 2022-12-13
### Corrigé
- problème d'annulation d'ordre
- problèmes de reconnexion des signaux

## [0.4.26] - 2022-12-12
### Corrigé
- requête graphql des stats

## [0.4.25] - 2022-12-12
### Corrigé
- Installation initiale des tentacles

## [0.4.24] - 2022-12-10
### Corrigé
- Surveillance des ressources système sur linux
- Calcul de la quantité d'ordre lorsqu'elle provient de la configuration
- Problèmes liés aux exchanges multiples
### Modifié
- Version de CCXT

## [0.4.23] - 2022-11-24
### Corrigé
- Surveillance des ressources système sur linux

## [0.4.22] - 2022-11-23
### Ajouté
- Surveillance des ressources système

## [0.4.21] - 2022-11-23
### Ajouté
- Quantité d'ordre dans la configuration des Trading modes
- Heure du dernier signal de copy trading
### Modifié
- Amélioration du temps de chargement de la page profil
### Corrigé
- Erreurs sur le clock synchronizer
- Suppression d'exchange se propageant aux profils

## [0.4.20] - 2022-11-13
### Modifié
- Gestion des exceptions
### Corrigé
- Crash sur stop loss

## [0.4.19] - 2022-11-01
### Modifié
- Détails d'authentification de la configuration d'exchange

## [0.4.18] - 2022-11-01
### Corrigé
- Ne pas utiliser l'environnement beta par défaut

## [0.4.17] - 2022-11-01
### Corrigé
- Dimensionnement des ordres de copy trading

## [0.4.16] - 2022-10-23
### Modifié
- Configuration du copy trading
- Configuration de CCXT via des variables d'environnement
### Corrigé
- Configuration de Dip Analyser
- Gestion des ordres Bitget & Coinex

## [0.4.15] - 2022-10-23
### Corrigé
- Copy trading
- Arrêt du strategy optimizer

## [0.4.14] - 2022-10-21
### Corrigé
- Crash sur le calcul du portefeuille historique
### Ajouté
- Fermeture de position depuis l'interface web
- Signaux lors de l'annulation d'ordre par l'utilisateur

## [0.4.13] - 2022-10-15
### Corrigé
- Calcul des frais en trading spot

## [0.4.12] - 2022-10-15
### Corrigé
- Copy trading

## [0.4.11] - 2022-10-14
### Ajouté
- Système d'entrées utilisateur
- Exchange Phemex
- Stockage des runs
### Modifié
- Configuration pour chaque tentacle
- Système de bots community au lieu des devices

## [0.4.10] - 2022-09-13
### Modifié
- Tentacles beta
### Corrigé
- Problèmes de rate limit Kucoin
- Problèmes de trading de futures
- Versionnage des tentacles lors de l'import de profil

## [0.4.9] - 2022-09-07
### Modifié
- Tentacles beta
### Corrigé
- Export de profil

## [0.4.8] - 2022-09-04
### Corrigé
- Création de device

## [0.4.7] - 2022-09-03
### Modifié
- [Astrolab] Améliorations et corrections

## [0.4.6] - 2022-08-23
### Ajouté
- [Trading] Trading de futures
- [Exchange] Bitget
- [Trading] Copy trading
- [Beta] Environnement beta
### Modifié
- [Community] Migration vers le site community mis à jour
### Corrigé
- [Websockets] Plusieurs problèmes liés au rafraîchissement des bougies

## [0.4.5] - 2022-06-12
### Corrigé
- [Trading modes] Les stop loss ne sont pas créés après des ordres limit instantanément exécutés
- [Exchanges] Plusieurs problèmes de backtesting
- [WebInterface] Tri de la valeur du portefeuille

## [0.4.4] - 2022-06-01
### Ajouté
- [Exchanges] Moteur de trading de futures
- [TradingModes]
  - Bases des trading modes scriptés
  - Bases des copy traders

### Corrigé
- [WebInterface] Problème de sécurité

## [0.4.3] - 2021-11-23
### Ajouté
- [Trading Modes] Ajout des paramètres de volume d'achat

### Corrigé
- [Orders] Problèmes de typage liés aux Decimal

## [0.4.2] - 2021-11-21
### Ajouté
- [WebInterface]
    - Ajout d'un filtre dans la matrice d'évaluation
    - Cache et compression
    - Import / Export de la liste de devises
    - Option pour changer le marché de référence sur les paires configurées
    - Message d'information sur le DataCollector et le Backtesting
    - Tri des devises par capitalisation boursière
- [Evaluators] SuperTrend

### Modifié
- [Profile][Art's scalp] Mise à jour du nom du canal telegram

### Corrigé
- [WebInterface]
    - Problème avec le menu déroulant sur firefox
    - erreur de decimal sur json

## [0.4.1] - 2021-10-15
### Ajouté
- [Interface][Telegram]
    - Redémarrage d'OctoBot
- [Interface][Web]
    - Bouton d'arrêt du DataCollector
    - Sélection de date du Backtesting
- [Evaluator] Death and golden cross
- [Exchanges][Partners] Ascendex

### Modifié
- [Websockets] Cryptofeed de < 2.0.0 à 2.0.1

### Corrigé
- Plusieurs problèmes de Websockets

### Supprimé
- [Infra] Nexus

## [0.4.0-beta17] - 2021-09-15
### Corrigé
- Problèmes de valorisation de marché des avoirs du portefeuille

## [0.4.0-beta16] - 2021-09-13
### Corrigé
- Problèmes d'affichage du portefeuille
- Problèmes d'ordres de vente du dip analyzer

## [0.4.0-beta15] - 2021-09-09
### Corrigé
- Problèmes de backtesting liés aux évaluateurs temps réel
- Plusieurs problèmes liés à decimal.Decimal
- Problèmes de parsing des ordres

## [0.4.0-beta14] - 2021-09-09
### Ajouté
- [Nouveau tentacle]
   - Évaluateur de signal IA d'Art
- [Web Interface]
   - Progression du collecteur de données historiques
- [Websockets] Les websockets Huobi & GateIO sont désormais disponibles
### Corrigé
- [Trader]
   - Correction de plusieurs problèmes d'arrondi
   - Correction de plusieurs problèmes d'erreur NegativePortfolio
   - Suppression de la limite de 2000 ordres
- [Websockets]
   - Optimisation de l'abonnement aux feeds
- [Evaluators]
   - Correction des évaluations indésirables des paires non négociées lors de l'utilisation des websockets
-
## [0.4.0-beta13] - 2021-08-12
### Ajouté
- [Site community]
   - Créez et liez votre compte dans OctoBot
   - Faites-nous savoir que vous avez effectué un don pour débloquer l'accès aux websockets sans aucune exigence d'exchange
- [Nouveaux sites de documentation]
   - Nouveau design pour docs.octobot.online
   - Developer.docs.octobot.online
   - Exchanges.docs.octobot.online
- [Data collector] (@valouvaliavlo) : peut désormais collecter des fichiers de données de plusieurs symboles
- [Websockets] Les websockets FTX & OKEx sont désormais disponibles
### Corrigé
- [Backtesting] Plusieurs bugs de backtesting liés aux évaluateurs temps réel
- [TA] Les évaluateurs techniques peuvent désormais utiliser la time frame temps réel

## [0.4.0-beta12] - 2021-07-12
### Corrigé
- [WebInterface] Configuration des Exchanges & du Webhook

## [0.4.0-beta11] - 2021-07-11
### Note
Merci à @valouvaliavlo pour son travail dans cette version !

### Ajouté
- [Backtesting] (@valouvaliavlo) : Collecte de données historiques sur une plage de dates
- [Webhooks] (@valouvaliavlo) : Les webhooks peuvent désormais être configurés sans Ngrok
- [Exchanges] : Soutenez OctoBot en utilisant Binance sans parrainage
- [Binance websocket] : Les bannissements liés au rate limit ne devraient plus se produire (disponible uniquement pour les comptes sans parrainage)

### Modifié
- [Documentation] Mise à jour de la documentation des webhooks
- [Configuration] Amélioration de la configuration des comptes d'exchanges
- [Future trading] Désormais proche d'être pris en charge en trading réel

## [0.4.0-beta10] - 2021-06-05
### Corrigé
- [Websockets] Gestion correcte des erreurs de websockets
- [Loggers] Mappage correct des arguments de logging par défaut

## [0.4.0-beta9] - 2021-04-31
### Ajouté
- [WebInterface] Statistiques OctoBot avancées
- [Exchanges] Connexions websocket en beta
- [Profiles] Profils par défaut pour chaque trading mode
- [Profiles] Profils en lecture seule

### Corrigé
- Commande d'arrêt

## [0.4.0-beta8] - 2021-04-06
### Ajouté
- [WebInterface] Tutoriel de démarrage
- [WebInterface] Bouton de bascule du trader
- [WebInterface] Mise à jour d'OctoBot

### Corrigé
- [WebInterface] Plusieurs corrections et améliorations
- [Trading] Correction de la configuration des paires avec wildcard
- [Exchanges] Correction de hitbtc
- [Trading] Problèmes d'arrondi lors de la création d'ordre

## [0.4.0-beta7] - 2021-03-26
### Ajouté
- Vérification de la configuration des GridOrders

### Corrigé
- Configuration des symboles avec wildcard
- Image docker raspberry armv7 (merci à @gabriel-milan)

## [0.4.0-beta6] - 2021-03-22
### Modifié
- URLs des sites web

## [0.4.0-beta5] - 2021-03-21
### Ajouté
- Trading modes grid orders
- Prise en charge de plusieurs exchanges
- Export des logs de l'interface web
- Commandes utilisateur pour interagir avec les trading modes
### Modifié
- Tri par date des fichiers de données de l'interface web
### Corrigé
- Problèmes d'exchanges (binance et kraken)

## [0.4.0-beta4] - 2021-02-16
### Modifié
- Interface web
### Corrigé
- Problèmes de synchronisation des exchanges

## [0.4.0-beta3] - 2021-02-08
### Ajouté
- Profils de configuration
### Modifié
- Interface web
### Corrigé
- Plusieurs problèmes liés aux exchanges

## [0.4.0-beta2] - 2020-12-10
### Modifié
- Interface web

## [0.4.0-beta1] - 2020-12-08
### Ajouté
- Logs d'exceptions

## [0.4.0-alpha27] - 2020-12-06
### Corrigé
- Problèmes de redémarrage

## [0.4.0-alpha26] - 2020-11-26
### Ajouté
- Healthcheck Docker

## [0.4.0-alpha25] - 2020-11-23
### Ajouté
- Authentificateur community
### Modifié
- Nettoyage du fichier de configuration
### Corrigé
- Divers problèmes de démarrage liés à la configuration

## [0.4.0-alpha24] - 2020-10-23
### Modifié
- Prise en charge de Python 3.8

## [0.4.0-alpha23] - 2020-09-02
### Modifié
- [Real trading] Mise à jour de la gestion du statut des ordres

## [0.4.0-alpha22] - 2020-08-23
### Ajouté
- [Real trading] Correction d'un problème de gestion des ordres

## [0.4.0-alpha21] - 2020-08-23
### Ajouté
- [Real trading] Correction des problèmes de synchronisation des ordres

## [0.4.0-alpha20] - 2020-08-03
### Ajouté
- [Real trading] Phase beta du trading réel

## [0.4.0-alpha19] - 2020-06-15
### Ajouté
- [Trading modes] Trading mode Arbitrage
- [Orders] Ordres trailing stop
- [Web interface] Connexion à l'interface web
### Modifié
- [Orders] Optimisation du système de mise à jour des ordres
- [Web interface] Bibliothèques de l'interface
### Corrigé
- [Web Interface] Problèmes de démarrage d'OctoBot

## [0.4.0-alpha18] - 2020-06-01
### Corrigé
- [Backtesting] Erreur liée au verrou des fichiers de données de backtesting

## [0.4.0-alpha17] - 2020-05-26
### Corrigé
- [Trades] Trades affichés avec un prix de 0

## [0.4.0-alpha16] - 2020-05-22
### Modifié
- [OctoBotPackage] Déplacement des ressources liées à OctoBot dans le dossier octobot
- [OctoBot services] Initialisation
### Corrigé
- [Trading] Divers bugs
- [StrategyOptimizer] Divers bugs

## [0.4.0-alpha15] - 2020-05-20
### Corrigé
- [Services] utilisation de l'init du canal des services

## [0.4.0-alpha14] - 2020-05-19
### Corrigé
- [StrategyOptimizer] problème de typage

## [0.4.0-alpha13] - 2020-05-18
### Corrigé
- [Exchanges] problèmes dans le parsing des données d'exchange d'OctoBot

## [0.4.0-alpha12] - 2020-05-17
### Corrigé
- [Exchanges] problèmes dans le parsing des données d'exchange d'OctoBot et la désactivation des exchanges

## [0.4.0-alpha11] - 2020-05-16
### Ajouté
- [Channel] Canal OctoBot
- [Backtesting] Prise en charge de plusieurs fichiers de backtesting

### Corrigé
- Plusieurs problèmes dans les packages requis par OctoBot

## [0.4.0-alpha10] - 2020-05-02
### Ajouté
- [Backtesting] Prise en charge du canal synchronisé

### Modifié
- [Tests] framework de stratégie et de TA
- [Tests] migration du framework de trading mode
- [Interfaces & Notifications] Suivi de la migration
- [Backtesting] Une seule instance est créée

### Corrigé
- [Tests] Timeout du stress test
- [Startup] Correction des appels d'API

Changelog pour 0.3.9-beta
====================
*Date de sortie : 24 avril 2020*

# Corrections de bugs :
    - Correction du sélecteur de crypto-monnaies de l'interface web
    - Correction du message d'aide de dépendance du Tentacles-manager

## [0.4.0-alpha9] - 2020-04-12
### Modifié
- [Start] Import de ConfigEvaluatorError depuis OctoBot-Commons

### Corrigé
- [Stop] erreur de récursion
-  en-têtes cython d'octobot_api

## [0.4.0-alpha8] - 2020-04-10
### Ajouté
- Création de la configuration en cas de dossier utilisateur manquant
- Génération du bot_id

### Modifié
- Refonte de l'organisation des fichiers Python
- Métriques vers community
- Helper de script

## [0.4.0-alpha7] - 2020-04-08
### Supprimé
- Cythonisation des tentacles

## [0.4.0-alpha6] - 2020-04-07
### Corrigé
- Imports avec wildcard

## [0.4.0-alpha5] - 2020-04-05
### Modifié
**Prérequis**
- Version de Commons à 1.3.5
- Version d'Evaluators à 1.4.3
- Version de Trading à 1.4.20
- Version d'Interfaces à 1.0.1
- Version de Notifications à 1.0.1
- cython à 0.29.16

Changelog pour 0.3.8-beta
====================
*Date de sortie : 28 décembre 2019*

# Tickets / pull requests concernés :
    #978 peut désormais appeler start.py depuis n'importe quel répertoire
    #991 ajout de la prise en charge de nouveaux types d'ordres d'exchange

# Corrections de bugs :
    - Correction des méthodes ccxt dépréciées
    - Correction d'une régression du websocket binance

# Nouvelles fonctionnalités :
    - Prise en charge de nouveaux types d'ordres

## [0.4.0-alpha4] - 2019-12-22
### Modifié
**Prérequis**
- Version de Commons à 1.2.0
- Version d'Evaluators à 1.3.1
- Version de Trading à 1.4.11
- jsonschema à 3.1.1

## [0.4.0-alpha3] - 2019-11-10
### Corrigé
- CI Appveyor
- Livraison pypi Travis

### Modifié
**Prérequis**
- Version de Cython à 0.29.14
- Version de Commons à 1.1.49
- Version d'Evaluators à 1.2.6
- Version de Trading à 1.4.5

## [0.4.0-alpha2] - 2019-10-31
### Corrigé
- Imports de la classe Commands
- Appels à start.py

## [0.4.0] - 2019-10-19
### Ajouté
- package principal octobot pour initialiser tous les packages d'OctoBot

### Déplacé
- Modules Evaluator liés à OctoBot-Evaluators
- Modules Trading liés à OctoBot-Trading
- Modules Services liés à OctoBot-Services
- Modules Common liés à OctoBot-Commons
- Modules Backtesting liés à OctoBot-Backtesting
- Modules Websocket liés à OctoBot-Websockets
- Modules Service liés à OctoBot-Services
- Modules Interface liés à OctoBot-Interface
- Modules Notification liés à OctoBot-Notifications

Changelog pour 0.3.7-beta
====================
*Date de sortie : 31 août 2019*

# Avertissement : le fichier config.json a été déplacé dans le dossier utilisateur

# Tickets / pull requests concernés :
    #948 [Trading] Ajout de la time frame 6h
    #949 [Config] Migration du fichier de configuration vers le dossier utilisateur enhancement
    #952 [Trader] Correction des ordres kraken
    #953 [Docker] Amélioration du dockerfile
    #955 [Backtesting] Amélioration de la génération des trades récents
    #960 [Backtesting] Utilisation de la dernière bougie pour le calcul de la rentabilité
    #962 [Portfolio] Stablecoins manquants dans le portefeuille négocié
    #964 [Backtesting][DipAnalyser] tentative de création d'un ordre de vente sans fonds suffisants
    #968 [Web interface] Gestion des erreurs
    #969 [Web interface] Ajout d'un bouton de rafraîchissement du real trader

# Corrections de bugs :
    - Correction des erreurs lors de la création d'ordres sur l'exchange Kraken
    - Correction des imprécisions du backtesting
    - Prend désormais correctement en compte chaque devise lors du calcul de la rentabilité et des avoirs
    - Correction des incohérences du simulateur d'exchange de backtesting

# Nouvelles fonctionnalités :
    - Ajout d'un bouton de rafraîchissement du real trader similaire à la commande telegram /refresh_real_trader dans l'interface web
    - Ajout de pages de gestion des erreurs dans l'interface web
    - Peut désormais gérer les time frames de 6 heures
    - Dockerfile optimisé

Changelog pour 0.3.6-beta
====================
*Date de sortie : 15 juillet 2019*

# Tickets / pull requests concernés :
    #922 [Notifications] Exception non interceptée lors d'une erreur de publication de notifications bug
    #937 [Exchanges] Échec du token API lorsque api-password est fourni mais non nécessaire bug
    #940 [Bug][High] Correction de la synchronisation horaire des bougies de l'updater
    #927 [Docker] exposition de l'interface web pour les communications inter-conteneurs
    #900 Correction de l'échec du config checker lors de l'utilisation de wildcard sur les paires
    #931 Amélioration de l'UI de la barre de navigation
    #944 Ajout d'un design switch pour les cases à cocher de configuration des tentacles

# Corrections de bugs :
    - Correction de l'erreur de token API d'exchange lors de la première installation
    - Correction du taux de mise à jour des time frames pour correspondre à la durée des time frames
    - Correction d'une exception de notification non interceptée
    - Correction de l'erreur de validation de la configuration avec wildcard

# Nouvelles fonctionnalités :
    - Ajout de la configuration des trading modes Daily et Signal
    - Amélioration de l'UI de l'interface web

Changelog pour 0.3.5-beta
====================
*Date de sortie : 27 mai 2019*

# Tickets / pull requests concernés :
    #894 [GlobalUpdater] ne met pas à jour les timeframes normalement lorsqu'il est notifié par RT
    #896 [Web interface] affichage des chiffres des très petits nombres
    #899 [Simulator] gel lors de la simulation d'ordres staggered
    #901 [Bug] Bougie perdue avec le websocket
    #904 [asyncio] optimisation de la gestion async
    #908 [Time frame updater] désynchronisation entre les heures de mise à jour des symboles

# Corrections de bugs :
    - Correction de l'affichage des chiffres dans la configuration de l'interface web
    - Correction des timings de rafraîchissement des time frames

Changelog pour 0.3.4-beta
====================
*Date de sortie : 12 mai 2019*

# Tickets / pull requests concernés :
    #191 [Kucoin] Tester OctoBot sur différents exchanges
    #696 [Tentacles config] ajout de l'édition de la configuration des tentacles dans l'interface web
    #782 [Notifiers] Suppression des systèmes de notification inutilisés
    #792 [Web interface][Configuration] forcer l'affichage des paramètres absents de config.json
    #804 [Web interface] Annulation des ordres selon le filtre du tableau
    #813 [Docker] Ajout d'une image docker raspberry
    #810 [WebInterface] ajout d'une barre de progression d'annulation des ordres
    #811 [Telegram interface] Démarrage plus facile de l'interface telegram
    #817 [WebInterface] Amélioration UX de la sélection courante de la barre de navigation
    #818 [Exchanges] Gestion des mots de passe d'API
    #820 [Exchanges] gestion de la création d'ordre lorsque l'ordre résultat n'est pas complet
    #821 [Exchange traded pairs] aucun message lorsqu'une paire négociée est indisponible
    #823 [Coinbase Pro] Tester OctoBot sur différents exchanges
    #824 [RealTrader] impossible de démarrer OctoBot en cas d'erreur de connexion au real trader
    #826 [Web interface] mise à jour du graphique de prix
    #830 [0.3.4][Exchange][REST] Officialisation de la prise en charge de Kucoin et CoinBasePro
    #832 [TradingModes] ne peut pas démarrer en cas d'erreur dans l'init du trading mode
    #834 [StrategyTestFramework] gestion d'un marché de référence différent
    #837 [EvaluatorCreator] crash sur exception dans __init__ de l'évaluateur
    #839 [WebInterface] rafraîchissement de l'interface de backtesting
    #847 [WebInterface] ajout des conditions d'utilisation
    #854 [TentacleManager] ModuleNotFoundError: No module named 'tentacles_manager'
    #865 [Exchange config] simplification de la configuration du token d'exchange
    #869 [Factorize] nouvelle classe abstraite "Tentacle"
    #870 [Traders] ne pas autoriser le simulateur et le real trader pendant la même exécution
    #873 [WebInterface] ne pas supprimer la configuration du symbole en l'absence d'exchange
    #875 Email Contact is Invalid
    #876 [TentacleManager]No module named 'evaluator.Util.advanced_manager'
    #887 [Metrics] ajout du type d'environnement d'exécution aux métriques (code, binaire, etc.)
    #889 correction du bug usdX dans le ws


# Nouvelles fonctionnalités :
    - Ajout de l'interface de configuration des tentacles :
        - Générée à partir du schéma json du fichier de configuration du tentacle
        - Permettant de backtester des stratégies/évaluateurs directement depuis l'interface web
    - Ajout de la prise en charge de Kucoin et CoinbasePro
    - Amélioration de l'UI et de l'UX de l'interface web
    - L'interface Telegram est désormais démarrée automatiquement une fois configurée
    - Possibilité de copier/coller les tokens d'exchange dans config.json : OctoBot les chiffrera ensuite
    - Impossible d'avoir simultanément un real trader et un trader simulator afin d'éviter les effets de bord
    - Image docker OctoBot pour RaspberryPie
    - Gère désormais les exchanges avec mots de passe d'API
    - Ajout d'un avertissement

# Corrections de bugs :
    - Correction de plusieurs bugs liés au démarrage d'OctoBot avec une erreur de configuration : démarre désormais et affiche les erreurs dans les logs de l'interface
    - Correction des crashs en cas d'erreur dans les Tentacles : affiche désormais le message d'erreur à la place
    - Correction de la mise à jour du graphique de prix dans l'interface web
    - Correction d'un bug de rentabilité dans la suite de tests de stratégie
    - Correction des bugs de rafraîchissement de l'interface web de backtesting
    - Correction de l'erreur d'import du tentacle manager
    - Correction de la suppression de la configuration des paires négociées en l'absence d'exchange disponible
    - Correction du contact email
    - Correction du bug avec les stablecoins USD sur le websocket

Changelog pour 0.3.3-beta
====================
*Date de sortie : 18 avril 2019*

# Tickets concernés :
    #425 [Telemetry] Création d'un daemon de télémétrie
    #731 [Trader] Permettre de démarrer à partir du dernier mouvement de l'exécution précédente
    #734 [Order] order_type n'est pas cohérent
    #740 [RunInAsyncMainLoop] problème avec les commandes d'exchange
    #741 [WebInterface] ajout de la possibilité d'annuler des ordres
    #747 [Backtesting] préparation pour de multiples formats de données
    #749 [Backtesting] impossible d'afficher les bougies sur une time frame spécifique depuis l'interface web
    #750 [OrderCreator] erreur lors du calcul du prix de l'ordre
    #751 [Backtesting] problème lors de la sauvegarde de la configuration depuis l'interface web en backtesting
    #752 [WebInterface] bug d'affichage des bougies
    #756 [OrderManager] call_order_update_callback non appelé lors d'une exception dans _update_order_status
    #785 [Metrics] affichage des métriques community
    #792 [Web interface][Configuration] forcer l'affichage des paramètres absents de config.json

# Nouvelles fonctionnalités :
    - Annulation des ordres depuis l'interface web
    - Métriques community via une télémétrie optionnelle et anonyme
    - Ajout de la sauvegarde et de la récupération de l'état du trader du bot
    - Ajout de commandes telegram

# Corrections de bugs :
    - Correction de plusieurs bugs liés aux traders
    - Correction d'un bug de timeout d'exchange
    - Correction des bugs de l'interface web
    - Correction des bugs du créateur d'ordres

Changelog pour 0.3.2-beta
====================
*Date de sortie : 10 mars 2019*

# Tickets concernés :
    #635 [Interface Bot] Nouvelles commandes pour le bot telegram, etc.
    #647 [Web interface] impossible d'ajouter plus d'une devise à la fois bug
    #655 [Configuration interface] ne pas afficher les évaluateurs en développement
    #661 HybridTradingMode.json NOT FOUND
    #663 [Telegram evaluator] ajout de l'architecture de dispatcher telegram
    #664 [SignalEvaluator] création d'un évaluateur de signal abstrait
    #665 [Evaluators] ajout d'une méthode pour connaître le type d'évaluation réalisée par l'évaluateur
    #667 [Web interface] ajout d'une option pour appliquer la configuration par défaut de la stratégie lors de son activation
    #671 [Telegram Interface] Amélioration de la lisibilité grâce au formatage des messages (markdown ?)
    #678 [Logs management] ne pas journaliser les erreurs deux fois
    #681 [Web Interface] amélioration du design des cases à cocher
    #684 [Telegram Interface] telegram.error.BadRequest: Message is too long
    #686 [Real Trader] trouver un moyen de gérer les prix d'exécution des ordres au marché lors de l'utilisation du ws
    #687 [Web Interface] Amélioration de la lisibilité du graphique des bougies & trades
    #691 [OrderManager] KeyError "Error when updating orders"
    #694 [TentacleEvolution] Préparation pour la stratégie staggered orders
    #697 [StopLoss] {"code":-2010,"msg":"Account has insufficient balance for requested action."} lors du déclenchement du stop loss
    #700 [Web interface] Filtrer les exchanges ccxt : ne pas afficher les exchanges inutilisables
    #702 [Portfolio display] La valeur totale du portefeuille n'est pas toujours mise à jour dans les interfaces web et telegram
    #705 [Interfaces] ajout de messages par défaut lorsqu'aucune donnée n'est disponible
    #711 [Bug] Trade creator : ne respecte pas systématiquement les règles d'ordre
    #713 [Telegram Interface] la commande /fees ne répond pas
    #715 [Order Manager] problème avec les stop losses sur les trades réels
    #717 [Real Trader] notification de remplissage d'ordre non reçue (web socket)

# Nouvelles fonctionnalités :
    - Nouvelle stratégie : staggered orders
    - Amélioration de l'expérience utilisateur des interfaces web et telegram
    - Ajout de la documentation et des paramètres par défaut des évaluateurs dans l'interface web
    - Ajout de commandes telegram
    - Peut désormais gérer les signaux telegram

# Corrections de bugs :
    - Correction de plusieurs bugs liés à la gestion et à la synchronisation des ordres
    - Correction d'un rare bug de synchronisation du portefeuille
    - L'interface telegram découpe désormais les longs messages
    - Correction des bugs de l'interface web
    - Correction de la commande telegram /fees

Changelog pour 0.3.1-beta
====================
*Date de sortie : 29 janvier 2019*

**Avertissement** :
- La version 0.3.0 nécessite de réinstaller tous les tentacles par défaut (start.py -p reset_tentacles && start.py -p install all)

# Tickets concernés :
    #624 correction des annonces hors ligne
    #629 correction des ordres stop multiples du real trader
    #631 correction du système d'arrondi de la gestion des poussières

# Nouvelles fonctionnalités :
    - Nettoyage des prérequis

# Corrections de bugs :
    - Correction de la livraison pip
    - Correction des ordres stop du real trader
    - Correction de la gestion des poussières
    - Corrections mineures sur le portefeuille

Changelog pour 0.3.0-beta
====================
*Date de sortie : 27 janvier 2019*

**Avertissement** :
- Nécessite désormais Python 3.7
- Nécessite de réinstaller tous les tentacles par défaut (start.py -p reset_tentacles && start.py -p install all)
- Si vous utilisez l'interface telegram, vous pouvez ajouter votre nom d'utilisateur telegram dans la whitelist de la configuration telegram

# Tickets concernés :
    #481 [Exchange] Utilisation de l'appel d'exchange async fourni par ccxt
    #495 [Global] refonte de l'architecture multi-thread en architecture async
    #502 [Setup] Mise à jour et amélioration de setup.py
    #505 [Web interface] ajout du support hors ligne complet pour l'ensemble du bot et des services & interfaces
    #506 [Profitability] ajout de la rentabilité hypothétique sans trades en utilisant le portefeuille initial
    #509 [Matrix] Migration vers dataclass
    #517 [Bug][Strategy Optimizer] impossible de changer de stratégie une fois la première sélectionnée dans l'interface web
    #526 [Docker] Migration vers python:3.7.2-slim-stretch
    #532 [PIP] Création du package pip OctoBot
    #533 [Security] Ajout d'un système d'authentification optionnel pour les interfaces externes
    #534 [Data collector] migration du datacollector autonome vers l'architecture async
    #536 [Installation doc] mise à jour du script d'installation raspberry
    #538 [Trader] erreur MIN_NOTIONAL lors de la création d'un ordre
    #539 [Web Interface] séparation de la configuration requise et des champs de création par défaut dans les services
    #540 [Web Interface] ajout d'informations d'aide sur les champs de configuration
    #543 [Async] Des avertissements Appveyor sont levés
    #549 launcher_windows.exe virus total
    #550 [Release] Ajout d'un checksum de release
    #553 [Release CI] Création d'un binaire macos à la release
    #561 [Notifier] Ajout des fournisseurs de notifier à l'interface web
    #567 [Notifier] ajout du support du notifier pour l'interface web
    #571 [User experience] ajout de documentation et de messages d'aide concernant la configuration et les interfaces
    #572 [Donation] ajout de systèmes de don
    #576 [Binary] Impossible de redémarrer le bot avec le binaire depuis l'interface
    #578 [Bug][Async] Impossible d'arrêter OctoBot correctement
    #585 [RestExchange] gestion récurrente des erreurs côté exchange
    #591 [User feedback] ajout de systèmes de feedback
    #592 démarrer sur un vps ?
    #593 [Web&Bot Interface] Ajout de la version d'OctoBot
    #594 [Tentacles] gestion des tentacles incompatibles
    #595 [GUI] Suppression du pre-launcher
    #596 [Web interface] gestion des avertissements récurrents "can't find matching symbol"
    #600 [Public Messages] ajout de la gestion des messages publics
    #603 [Web interface] gestion des bougies depuis la page d'index lorsque le bot vient de démarrer et que les données ne sont pas disponibles
    #606 [Web interface] correction de l'affichage du bouton de lien firefox

# Nouvelles fonctionnalités :
    - Architecture asyncio complète pour le moteur central du bot
    - Remplacement de la fenêtre launcher TK par un launcher web
    - Vérifie désormais les versions et la validité des tentacles à l'initialisation
    - Ajout de la rentabilité du portefeuille initial
    - Peut désormais ajouter une whitelist d'utilisateurs sur l'interface telegram
    - Amélioration de l'expérience utilisateur de l'interface web
    - Ajout de plusieurs systèmes d'aide dans l'interface web
    - Ajout de la version actuelle d'OctoBot dans les interfaces web et telegram
    - Peut désormais afficher des annonces globales
    - Ajout des adresses de don
    - Ajout de plusieurs nouveaux systèmes de notification
    - Peut désormais arrêter et redémarrer correctement OctoBot depuis l'interface web
    - Peut désormais arrêter OctoBot correctement avec CTRL+C
    - Optimisation de l'exécution grâce aux data classes
    - Ajout d'un mode hors ligne avec des options limitées
    - Testé sur MacOS X
    - Octobot disponible sur PIP
    - Réduction de la taille de l'image Docker
    - Ajout d'un checksum sur les versions binaires

# Corrections de bugs :
    - Peut désormais changer la stratégie sélectionnée lors d'appels multiples de l'optimizer
    - Peut désormais redémarrer OctoBot depuis l'interface web
    - Ne spammera plus l'avertissement can't find matching symbol
    - Correction des bugs d'affichage Firefox dans l'interface web
    - Gère désormais les erreurs survenant côté API rest des exchanges

Changelog pour 0.2.4-beta
====================
*Date de sortie : 30 décembre 2018*

# Tickets concernés :
    #433 [Style] Correction des erreurs de code
    #446 ajout de la resync du real trader sur InsufficientFunds
    #448 ajout de la commande telegram refresh_real_trader
    #450 correction de la vérification de la configuration au démarrage des services
    #456 Implémentation de la persistance de la configuration docker
    #457 amélioration de l'UX du data collector et du sélecteur de vue de marché
    #461 correction du bug de la carte générique avec les noms contenant des espaces
    #474 Implémentation du correcteur de statut de marché d'exchange
    #475 suppression du saut de ligne final
    #477 ajout de l'affichage de la stack trace sur toutes les exceptions pertinentes
    #483 correction des ajouts multiples dans la liste des classes
    #486 Refonte de la classe Trade

# Nouvelles fonctionnalités :
    - Image Docker prête
    - Commande telegram de rafraîchissement forcé
    - Correcteur de statut de marché d'exchange
    - Mise à jour de la version de python vers python 3.7.2

# Corrections de bugs :
    - Correction des couleurs de marge de trading
    - Correction de la nouvelle version de l'api binance
    - Correction du bug d'effacement lors du chargement de la configuration
    - Corrections web mineures

Changelog pour 0.2.3-beta
====================
*Date de sortie : 17 novembre 2018*

# Tickets concernés :
    #359 [Web Interface][User experience] Amélioration de l'ordre des sélecteurs de time frame
    #421 [Web Interface] Ajout d'une représentation graphique des avoirs du portefeuille

# Nouvelles fonctionnalités :
    - Avoirs graphiques du portefeuille

# Corrections de bugs :
    - Correction des erreurs dans le calcul de la rentabilité
    - Correction du dockerfile
    - Ne pas afficher les logs des interfaces lorsqu'elles sont désactivées (ex : telegram)

Changelog pour 0.2.2-beta
====================
*Date de sortie : 04 octobre 2018*

# Tickets concernés :
    #359 [Web Interface][Configuration] Amélioration de l'interface utilisateur
    #406 [backtesting] ajout d'un argument de démarrage pour mettre le bot en pause à la fin du backtesting afin d'analyser les résultats
    #408 [Nouvelle stratégie de trading] implémentation d'une nouvelle stratégie de trading utilisant des évaluateurs temps réel et la TA
    #410 [Websocket] erreur lors de l'ouverture d'un websocket avec des symboles traduits
    #413 [Web interface] ajout de la visualisation des prix pour chaque symbole
    #414 [Web interface] Personnalisation du tableau de bord
    #417 [Evaluator configuration] informer l'utilisateur en cas d'évaluateurs requis manquants

# Nouvelles fonctionnalités :
    - Personnalisation du tableau de bord

# Corrections de bugs :
    - Correction de l'erreur lors de l'ouverture d'un websocket avec des symboles traduits

Changelog pour 0.2.1-beta
====================
*Date de sortie : 25 septembre 2018*

# Tickets concernés :
    #359 [Web Interface][Configuration] Amélioration de l'interface utilisateur
    #399 Erreur au démarrage du backtesting : 'backtesting'
    #401  [GUI] refonte des packages de l'interface gui locale

# Nouvelles fonctionnalités :
    - Améliorations du launcher

# Corrections de bugs :
    - Correction de la configuration par défaut du backtesting

Changelog pour 0.2.0-beta
====================
*Date de sortie : 5 septembre 2018*

**Version majeure : Open beta d'OctoBot**


# Tickets concernés :
    #288 [Binance Websocket] Gestion de la maintenance de l'exchange et de la reconnexion du websocket
    #291 [RestExchange] remplir les données de retour avec des valeurs par défaut en cas de valeurs et d'éléments manquants
    #344 [Notifications] gestion du prix des ordres au marché
    #353 [Exchange Simulator] Ajout des frais
    #359 [Web Interface][Configuration] Amélioration de l'interface utilisateur
    #376 [Tentacles] Trading_config.json
    #377 [Web interface] Configuration avancée des évaluateurs (TA, RT, Social)
    #378 [Web interface] Affichage des erreurs et avertissements (icônes du menu supérieur)
    #379 [Web interface] Page de configuration du trading mode et de la stratégie
    #385 [Web Interface] ajout de la rentabilité du bot
    #389 [Web Interface] ajout d'une page de statut de marché
    #393 [Web Interface] ajout d'informations sur les trading modes et les évaluateurs

# Nouvelles fonctionnalités :
    - Première version de l'interface web complète
    - Les versions binaires d'OctoBot et de son launcher sont désormais disponibles
    - Simulation des frais en mode simulation
    - Reconnexion automatique des web sockets lors de la maintenance de l'exchange
    - Amélioration de la configuration par défaut à la première utilisation

# Corrections de bugs :
    - Notification d'ordre au marché sans prix

Changelog pour 0.1.7-beta
====================
*Date de sortie : 15 août 2018*

**Avertissement** :
- La clé de trading a changé : [Voir la page trading du wiki](https://github.com/Drakkar-Software/OctoBot/wiki/Trading)


# Tickets concernés :
    #218 [Bin] Réflexion sur le binaire octobot
    #288 [Binance Websocket] Gestion de la maintenance de l'exchange et de la reconnexion du websocket
    #305 [Refactor] refonte du code global
    #321 [Web Interface] ajout d'une section backtesting
    #342 [Web Interface] Gestion des fonctionnalités de sauvegarde et de réinitialisation côté front
    #343 [Web Interface] Gestion de la suppression des éléments de carte
    #347 [Web Interface] Ajout du strategy optimizer dans le backtesting
    #355 [Bug] Les StopLossOrders mettent le portefeuille en négatif lors du backtesting
    #356 [Web Interface] Octobot ne redémarre pas au clic
    #359 [Web Interface][Configuration] Amélioration de l'interface utilisateur
    #360 [Web Interface] Ajout d'une section d'enregistrement des données
    #368 [Experiment][Web interface] sans dash
    #369 [Configuration] Séparation des paramètres de trading dans une section trading au lieu de trader
    #373 [Interface] Création du launcher
    #374 [Configuration] Suppression du websocket de la configuration et utilisation par défaut lorsqu'il est disponible

# Nouvelles fonctionnalités :
    - Application TK
    - Application d'installation
    - Interface web : backtesting & data collector
    - Améliorations du strategy optimizer
    - Interface web : réinitialisation & suppression dans la configuration
    - Interface web : accueil avec tableau de bord personnalisé

# Corrections de bugs :
    - Les StopLossOrders mettent le portefeuille en négatif lors du backtesting
    - Correction des problèmes de l'interface de configuration par défaut

Changelog pour 0.1.6_1-beta
====================
*Date de sortie : 1 août 2018*

# Tickets concernés :
    #346 refonte des pages tentacles et packages
    #347 initialisation de la page strategy optimizer
    #350 [Web Interface] thème noir
    #355 [Bug] Les StopLossOrders mettent le portefeuille en négatif lors du backtesting

# Nouvelles fonctionnalités :
    - Interface web : Strategy optimizer

# Corrections de bugs :
    - Correction du backtesting multi-symboles

Changelog pour 0.1.6-beta
====================
*Date de sortie : 30 juillet 2018*

**Avertissement** :
- Le type de notification a changé : [Voir la page notification du wiki](https://github.com/Drakkar-Software/OctoBot/wiki/Notifications)

# Tickets concernés :
    #310 [Web Interface] Configuration des notifications
    #335 [Notification] Refonte du système de type de notification
    #340 [Strategy optimizer] ajout du trading mode et du nombre moyen de trades dans le rapport final
    #341 Web Interface] Configuration des devises et des services
    #345 [Notification] Ajout du type de notification web

# Nouvelles fonctionnalités :
    - Interface web : améliorations de la configuration des Services, Exchange, Symboles
    - Amélioration du Strategy optimizer

Changelog pour 0.1.5_3-beta
====================
*Date de sortie : 26 juillet 2018*

**Avertissement** :
- Toutes les clés de configuration avec "_" changées en "-" (par exemple crypto_currencies -> crypto-currencies)

# Tickets concernés :
    #312 [Web Interface] Configuration des services
    #311 [Web Interface] Configuration des symboles
    #334 [Strategy configuration] création d'un optimizer de configuration de stratégie

# Nouvelles fonctionnalités :
    - Interface web : Configuration des services & symboles
    - Strategy optimizer
    - Commande encrypter

Changelog pour 0.1.5_2-beta
====================
*Date de sortie : 24 juillet 2018*

**Avertissement** :
- Vous devez chiffrer votre token d'exchange : **veuillez exécuter python tools/temp_encrypt_tool.py**
- La clé de type de notification est passée de "type" à "notification_type"

# Tickets concernés :
    #269 [Tool] Implémentation de ConfigManager
    #307 [Tentacle Installation] Ajout d'une nouvelle clé dans la description
    #309 [Web Interface] Configuration de l'exchange
    #331 [Security] Chiffrement de la clé api de l'utilisateur

# Nouvelles fonctionnalités :
    - Chiffrement de la clé api
    - Interface web : Configuration de l'exchange

Changelog pour 0.1.5_1-beta
====================
*Date de sortie : 17 juillet 2018*

# Tickets concernés :
    #305 [Refactor] refonte du code global
    #318 [Candles management] adaptation du timestamp des bougies pour avoir un timestamp en secondes partout
    #319 [Web interface] les trades sont affichés pour tous les symboles, n'afficher que pour celui sélectionné
    #320 [Backtesting] ne pas démarrer les services inutiles en mode backtesting
    #322 [Web interface] Création de la page portefeuille
    #323 [Web interface] Création de la page ordres
    #324 [Web interface] Création de la page trades

# Nouvelles fonctionnalités :
    - Amélioration de la prise en charge multi-symboles du backtesting
    - Rapport de backtesting à la fin d'un backtesting
    - Interface web : Nouvelles pages (portefeuille, ordres, trades)

# Améliorations :
    - Amélioration de la lisibilité de l'interface web

# Corrections de bugs :
    - Les timestamps des trades de backtesting étaient erronés lors du backtesting multi-symboles

Changelog pour 0.1.5-beta
====================
*Date de sortie : 15 juillet 2018*

# Tickets concernés :
    #252 [OrderManager] "Timed Out" levé pendant _update_orders_status
    #265 [Web Interface] Création de l'interface web d'édition d'evaluator_config.json
    #266 [Web Interface] Création de l'interface web du tentacles manager
    #270 [Web interface] Création d'une interface web avancée
    #294 [Trader simulator] Les ordres StopLoss se déclenchent alors qu'ils ne le devraient pas
    #302 [Web Interface] mise en place de l'architecture
    #304 [Trade Manager] Assurer la résilience de get_average_market_profitability
    #308 [Backtesting] Amélioration de la précision du backtesting

# Nouvelles fonctionnalités :
    - Nouvelles fonctionnalités dans l'interface web : configuration des tentacles, trades affichés dans l'onglet Dashboard
    - Le backtesting est désormais pleinement opérationnel
    - Optimisation des opérations sur les chaînes de caractères

# Corrections de bugs :
    - Correction de rares exceptions sur la notification d'ordre via Telegram
    - Correction du caractère aléatoire du backtesting
    - Correction des ordres déclenchés à tort en mode simulateur

# Notes :
    - Désactivation de l'indicateur de stats Google par défaut en attendant une solution à la limite de requêtes


Changelog pour 0.1.4_4-beta
====================
*Date de sortie : 9 juillet 2018*

**Avertissement** :
- Réinstallez vos tentacles

# Tickets concernés :
    #265 [Web Interface] Création de l'interface web d'édition d'evaluator_config.json
    #266 [Web Interface] Création de l'interface web du tentacles manager
    #288 [Binance Websocket] Gestion de la maintenance de l'exchange
    #289 [Profitability] Ajout du changement moyen du marché lors de l'affichage de la rentabilité
    #290 [TimeFrames] Assurer la gestion des time frames non prises en charge par les exchanges
    #294 [Trader simulator] Les ordres StopLoss se déclenchent alors qu'ils ne le devraient pas
    #299 [OrderCreator] modification de la gestion du nombre minimal de chiffres

# Nouvelles fonctionnalités :
    - Nouvelles fonctionnalités dans l'interface web : configuration des évaluateurs, affichage des tentacles
    - Calcul de la rentabilité du marché

# Correction de bugs :
    - Correction de la gestion de la maintenance du websocket Binance
    - Correction du stop loss en mode simulateur
    - Correction des bugs de chiffres

Changelog pour 0.1.4_3-beta
====================
*Date de sortie : 3 juillet 2018*

**Avertissement** :
- Mettez à jour vos tentacles de trading mode

# Tickets concernés :
    #286 [Trading Mode] Refonte

# Nouvelles fonctionnalités :
    - Refonte du trading mode qui le rend multi-symboles

Changelog pour 0.1.4_2-beta
====================
*Date de sortie : 3 juillet 2018*

# Tickets concernés :
    #281 [Tentacles] gestion des tentacles en développement
    #283 [Tentacle Strategies & Trading Mode] ajout de constantes dans les fichiers de configuration

# Nouvelles fonctionnalités :
    - Tentacles en développement
    - Création de la configuration des Strategies et du Trading Mode avec le tentacle creator

Changelog pour 0.1.4_1-beta
====================
*Date de sortie : 1 juillet 2018*

# Tickets concernés :
    #279 [Trading Modes] préparation du bot pour un trading mode haute fréquence

Changelog pour 0.1.4-beta
====================
*Date de sortie : 1 juillet 2018*

**Info** :
- Nouveau package pip à installer "gitpython"

# Tickets concernés :
    #188 [Exchange data] nettoyage de la liste des ordres (clôturés et annulés) et autres anciennes données après 1 jour
    #263 [TentacleCreator] révision de la création des tentacles
    #273 [Web interface] Implémentation des commandes
    #274 problème d'installation
    #276 [Bug] Exception de l'interface web lorsqu'aucun exchange n'est spécifié

# Nouvelles fonctionnalités :
    - Mise à jour / Redémarrage / Arrêt d'Octobot depuis l'interface web

# Correction de bugs :
    - Correction du Tentacle Creator (-c)
    - Correction de la configuration sans exchange ou sans crypto-monnaie spécifié (web)

Changelog pour 0.1.3_2-beta
====================
*Date de sortie : 27 juin 2018*

# Tickets concernés :
    #264 [Web Interface] Création de l'architecture web
    #267 [Web interface] Gestion du statut d'octobot
    #268 [Web Interface] Gestion des notifications du bot
    #269 [Tool] Implémentation de ConfigManager
    #270 [Web interface] Création d'une interface web avancée

# Nouvelles fonctionnalités :
    - Squelette de l'interface web
    - Notifications dans l'interface web

# Correction de bugs :
    - Correction de la reconnexion reddit

Changelog pour 0.1.3_1-beta
====================
*Date de sortie : 25 juin 2018*

# Tickets concernés :
    #251 [Tests] Amélioration de la couverture de tests

# Correction de bugs :
    - Correction des commandes telegram
    - Correction des données de symbole d'exchange
    - Correction du watcher reddit

Changelog pour 0.1.3-beta
====================
*Date de sortie : 23 juin 2018*

# Tickets concernés :
    #251 [Tests] Amélioration de la couverture de tests
    #254 [Tool] Outil de création de tentacle

# Nouvelles fonctionnalités :
    - Outil de création de tentacle
    - Bases du trading haute fréquence [voir le tentacle public](https://github.com/Drakkar-Software/OctoBot-Tentacles/issues/2)

Changelog pour 0.1.2_4-beta
====================
*Date de sortie : 22 juin 2018*

# Tickets concernés :
    #256 Implémentation d'un trading mode multi-decider

# Nouvelles fonctionnalités :
    - Gestion multi-decider pour les trading modes

# Correction de bugs :
    - Correction de l'installeur linux
    - Correction du Subportfolio

Changelog pour 0.1.2_3-beta
====================
*Date de sortie : 21 juin 2018*

# Tickets concernés :
    #232 [Performances] Ajout de tests de performance pour les évaluateurs
    #233 [Tentacles tests] ajout d'un framework de test des tentacles
    #234 [TentacleManager] harmonisation du nommage des packages, tentacles et modules
    #235 [TentacleManager] ajout d'informations de progression
    #250 [Trade creator] vérification des ordres au prix de marché dans le simulateur
    #251 [Tests] Amélioration de la couverture de tests

# Nouvelles fonctionnalités :
    - Améliorations du Tentacle Manager

# Correction de bugs :
    - Correction de l'ordre au marché en mode simulateur
    - Correction du Rest exchange pour prendre en charge des exchanges supplémentaires

Changelog pour 0.1.2_2-beta
====================
*Date de sortie : 19 juin 2018*

# Tickets concernés :
    #193 [Bittrex] Tester OctoBot sur différents exchanges
    #232 ajout de tests de performance pour le stress test des évaluateurs
    #235 ajout d'informations de progression dans le tentacles manager
    #243 [Config] Correction de la description de l'Exception
    #245 [TentacleManager] ajout d'une confirmation avant de supprimer des fichiers
    #247 [OrderCreator] test de la fonction get_additional_dusts_to_quantity_if_necessary

# Nouvelles fonctionnalités :
    - OrderCreator : Prise en compte des poussières potentielles lors de la création d'un ordre

# Correction de bugs :
    - Correction du backtesting
    - Correction du Rest exchange pour prendre en charge des exchanges supplémentaires

Changelog pour 0.1.2_1-beta
====================
*Date de sortie : 18 juin 2018*

# Tickets concernés :
    #216 Activation du démarrage/arrêt des stratégies et de leurs évaluateurs à la demande

# Nouvelles fonctionnalités :
    - Activation et désactivation des tentacles liés à une stratégie

# Correction de bugs :
    - Deadlock de mise à jour du statut de l'ordre lors de l'annulation d'un ordre

Changelog pour 0.1.2-beta
====================
*Date de sortie : 16 juin 2018*

**Info** :
- Nouveau package pip à installer "tulipy"
- config.json se trouve désormais dans le dossier racine d'Octobot

# Tickets concernés :
    #214 [Time frames] Configuration des timeframes au setup d'OctoBot selon les exigences de timeframe des stratégies pertinentes
    #220 [Tentacle Manager] Implémentation de la commande de mise à jour
    #224 [TA calulation] Étude de la lib tulipindicators
    #225 [Telegram] ajout d'une commande get strategies and modes
    #226 [Data] Stockage des bougies de symbole dans une classe dédiée
    #229 [Tentacle Manager] ajout du nettoyage et de l'aide
    #230 [Architecture] Extraction des Tentacles et de la configuration du dossier de code
    #231 [Architecture] evaluator_config.json mis à jour par le Tentacle Manager

# Nouvelles fonctionnalités :
    - Gestion des Tentacles : mise à jour, gestion des versions
    - Migration des indicateurs TA-lib vers tulipy
    - Nouvelle commande de l'interface Telegram
    - Améliorations de l'architecture

Changelog pour 0.1.1-beta
====================
*Date de sortie : 8 juin 2018*

# Tickets concernés :
    #197 Ajout d'une configuration spécifique à l'évaluateur dans l'installation du tentacle
    #211 [Order Management] définition de la période de rafraîchissement au démarrage d'OctoBot
    #212 [Tentacles management] ajout de la gestion des dépendances
    #213 [Tentacles management] ajout d'un système de suppression de tentacle
    #215 [Trading mode] Ajout de la gestion de la configuration
    #217 [Trading Mode] Implémentation de plusieurs mini créateurs (avec une partie du pf)

# Nouvelles fonctionnalités :
    - Gestion des Tentacles : désinstallation, prérequis, fichiers de configuration

Changelog pour 0.1.0_2-beta
====================
*Date de sortie : 3 juin 2018*

**Info** :
- Config : clé "mode" ajoutée à "trader"

# Tickets concernés :
    #198 [Order Creation] Implémentation de la nouvelle architecture

# Nouvelles fonctionnalités :
    - Trading modes

Changelog pour 0.1.0_1-beta
====================
*Date de sortie : 2 juin 2018*

# Correction de bugs :
    #201 [Real trading] Correction d'un bug lors du chargement de l'ordre courant de l'exchange

Changelog pour 0.1.0-beta
====================
*Date de sortie : 1 juin 2018*

**Info** :
- Config : clé racine "packages" renommée en "tentacles"

# Tickets concernés :
    #108 [RoadMap] mise en forme de la RoadMap en une image attrayante
    #109 [RoadMap] ajout d'un tracker de RoadMap dans le ReadMe.md
    #136 [Tests] Amélioration de la couverture des tests de trading
    #139 [Tests] Amélioration de la couverture des tests de gestion des évaluateurs
    #156 [Documentation] Ajout de documentation pour les classes de gestion des évaluateurs
    #163 [Exchanges Tests] implémentation des web sockets pour les tests binance
    #164 [ReadMe] rendre le readme attrayant !
    #174 Renommage de CryptoBot en Octobot
    #181 [Telegram] Mise en pause et reprise du trading
    #183 Impossible de créer un ordre lorsque l'ordre est déjà sur l'exchange au démarrage du bot
    #186 [Twitter Interface] Certaines notifications ne sont pas envoyées sur le site Twitter

# Nouvelles fonctionnalités :
    - Mise en pause / reprise du trading via Telegram
    - Magnifique README et logo
    - Création d'une roadmap
    - Amélioration de la couverture de tests

# Correction de bugs :
    - Correction du portefeuille négatif en simulation

Changelog pour 0.0.12-alpha
====================
*Date de sortie : 26 mai 2018*

**Info** :
- Config : clé racine "data_collector" supprimée
- Backtesting : clé racine "file" changée en "files" sous forme de tableau
- Package Manager : nécessite d'exécuter `python3 start.py -p install all` pour installer les évaluateurs

# Tickets concernés :
    #84 [Environment] Création du docker
    #86 [CI] Implémentation de tiers
    #139 [Tests] Amélioration de la couverture des tests de gestion des évaluateurs
    #144 [Bug] Investigation du portefeuille simulé négatif de la version 0.0.11
    #145 [Datacollector] Implémentation de symboles multiples
    #146 [Backtesting] Implémentation de symboles multiples
    #147 [Backtesting] Implémentation d'exchanges multiples
    #148 [Backtesting] Implémentation de meilleures fonctionnalités de backtesting de l'order manager
    #151 [Services] journalisation d'un message d'information au démarrage
    #152 [Wiki] complétion de la version 1 du wiki
    #153 [Beta Version] Préparation de la version beta
    #154 [Exchanges] implémentation des web sockets pour l'exchange binance
    #155 [TA] amélioration de l'évaluateur temps réel
    #157 [Exchanges] gestion de la disponibilité des websockets dans l'exchange manager
    #158 [Order management] implémentation du callback de mise à jour d'ordre pour les websockets en plus des mises à jour par poll
    #159 ajout de la gestion cyclique des fichiers de log
    #160 [Real Trader] prise en compte du symbole de l'exchange et des exigences minimales de trade
    #161 [Evaluators] Autorisation de la création d'évaluateurs en cours d'exécution
    #162 [Services] Autorisation de la création de services en cours d'exécution
    #163 [Exchanges Tests] implémentation des web sockets pour les tests binance
    #165 Bump de matplotlib de 2.0 à 2.2.2
    #166 [Tests] Tests des fonctionnalités
    #171 [Package Manager] Prototype
    #172 [Telegram Interface] Aucune réponse à la demande de rentabilité
    #175 Ajout de tests pour la création d'ordres
    #176 [Package manager] implémentation des évaluateurs avancés

# Nouvelles fonctionnalités :
    - Data collector multi-symboles / exchanges
    - Backtesting multi-symboles
    - Wiki complété
    - Gestion des websockets
    - Gestion des exchanges
    - Websocket Binance
    - Journalisation cyclique
    - Gestion du redémarrage des évaluateurs & services
    - Package Manager
    - Installeur Windows

# Correction de bugs :
    - Amélioration de la qualité du code
    - Correction d'une exception dans update_status de l'ordre lors du backtesting
    - Correction du bug de remplissage d'ordre en simulation
    - Correction de l'absence de réponse de telegram à la commande /profitability
    - Prise en compte du symbole de l'exchange et des exigences minimales de trade


Changelog pour 0.0.11-alpha
====================
*Date de sortie : 11 mai 2018*

**Info** :
- Config : clé racine "simulator" changée en "trader_simulator"

**Avertissement** :
- <span style="color:red">Le trading réel est en version pre-alpha</span>

# Tickets concernés :
    #87  [Interface] Prototype de l'interface telegram
    #132 [Web] : ajout d'une vue du portefeuille
    #133 [Backtesting] Implémentation du rapport
    #134 [Order Creation] Correction de la quantité négative
    #135 [Simulation] Correction de l'order manager et du trades manager
    #136 [Tests] Amélioration de la couverture des tests de trading
    #138 [Trading] Implémentation des trades réels
    #139 préparation des tests des évaluateurs
    #140 [Trading] Implémentation de la gestion réelle du portefeuille
    #141 [Trading] Implémentation de la gestion réelle des ordres
    #142 [Timeframe manager] Implémentation

# Nouvelles fonctionnalités :
    - Améliorations de l'interface web
    - Interface Telegram
    - Notifications Telegram
    - Outil Pretty Printer
    - Gestion de l'expiration de la note d'évaluation
    - Début de l'implémentation du trading réel
    - Plusieurs nouveaux tests pour améliorer la couverture du code
    - TimeFrame Manager

# Correction de bugs :
    - Correction de la création d'ordre de la simulation de trader
    - [Order Creation] Correction de la quantité négative

Changelog pour 0.0.10-alpha
====================
*Date de sortie : 5 mai 2018*

# Tickets concernés :
    #63 Calcul de la note de divergence de l'évaluateur
    #86 [CI] Implémentation de tiers
    #117 adaptation automatique de la configuration des symboles pour le backtesting
    #119 Architecture de test TA
    #120 [Backtesting] Test de l'implémentation de la lib Zipline
    #121 ajout des données de pump soudain et description des données bank
    #122 ajout de test_reaction_to_over_bought_then_dip à tous les TA
    #123 ajout du test de hausse après survente pour tous les TA
    #124 ajout des tests de tendance plate sur tous les TA
    #125 [Notification] Double notification lorsqu'un ordre lié est annulé
    #127 ajout de la liste des indicateurs dans le graphique de prix d'entrée et de sortie
    #126 [Order] Trop d'ordres annulés lorsque des évaluateurs RealTime sont créés
    #128 [Notification] Aucune notification de rentabilité
    #129 [Web] Création d'un prototype d'interface web

# Nouvelles fonctionnalités :
    - Prototype d'interface web
    - Tests complets des patterns TA
    - Data Visualiser
    - Performance Analyser
    - Démarreur de bot avec options
    - Plusieurs nouveaux tests pour améliorer la couverture du code

# Correction de bugs :
    - Correction de la logique de risque avec les ordres au marché
    - Correction des notifications : uniquement le symbole concerné
    - Correction de la configuration par défaut
    - Correction du style du datavisualiser
    - Correction des noms de paramètres de la méthode surchargée de RedditEvaluator
    - Correction de la notification de rentabilité du portefeuille


Changelog pour 0.0.9-alpha
====================
*Date de sortie : 30 avril 2018*

# Tickets concernés :
    #20 ajout du service reddit et démarrage du dispatcher reddit
    #22 ajout du récupérateur d'actualités de pages web
    #47 backtesting
    #76 data collector
    #92 [Evaluators] Activation / désactivation via fichier de configuration
    #102 ajout de l'évaluateur avancé dans le handler du dispatcher
    #103 [Portfolio] Implémentation des pytests en dernier
    #104 Exchange Manager
    #105 correction de la notification d'annulation
    #107 factorisation des threads de rafraîchissement en un par symbole
    #113 Correction de la gestion du bug de portefeuille

# Nouvelles fonctionnalités :
    - Backtesting
    - Data Collector
    - Data Collector Parser
    - Exchange Manager
    - Nouvel évaluateur social (reddit, médias postés sur twitter & sites web)
    - Implémentation et couverture des tests

# Correction de bugs :
    - Correction de la gestion du Portfolio
    - Correction d'un bug critique sur l'évaluateur de symbole
    - Correction d'un bug critique dans la création d'ordre
    - Correction du join du trader
    - Correction des tests
    - Correction des constantes temps réel
    - Correction de l'installation raspberry de la nouvelle dépendance
    - Correction de la note en attente de l'évaluateur de fluctuation instantanée temps réel
    - Correction du style de notification de fin d'ordre
    - Correction de l'accès concurrent au portefeuille

Changelog pour 0.0.8-alpha
====================
*Date de sortie : 24 avril 2018*

# Tickets concernés :
    #26 évaluateur de moyenne mobile optimisé
    #90 ajout de la méthode can_create_order() pour vérifier si un ordre peut être émis
    #91 refactorisation des dispatchers
    #93 [Profitability] Correction d'une erreur de calcul
    #97 [Order] Correction de l'annulation d'ordre lors d'un changement d'état
    #99 [Symbol evaluator] L'évaluateur de symbole échoue à gérer plusieurs exchanges
    #100 [Exchanges] Implémentation de l'instanciation automatique de l'exchange lorsque les clés sont dans config.json


# Nouvelles fonctionnalités :
    - Nouveaux évaluateurs TA : DoubleMA, BollingerBand, ADX, MACD
    - Gestion du risque de trading (prix d'ordre, quantité d'ordre, seuils d'état final)

# Correction de bugs :
    - Correction des constantes dans la création d'ordre
    - Correction de la notification de fin d'ordre
    - Correction du prix Limit de 10% à 5% max
    - Correction des notifications gmail
    - Correction de l'évaluateur final & ajout de la notification de démarrage
    - Correction de la rentabilité du portefeuille
    - Correction de l'annulation d'ordre lors d'un changement d'état

Changelog pour 0.0.7-alpha
====================
*Date de sortie : 21 avril 2018*

# Tickets concernés :
    #26 ajout du momentum bollinger et de la gestion utilitaire avancée
    #48 [Portfolio] Gestion de la disponibilité des devises
    #51 [Trade / Trade Simulator] Implémentation de la rentabilité
    #68 Création de l'Advanced list manager
    #69 correction de la disponibilité et création de la notification de rentabilité par mail
    #70 [Trading Simulator] Gestion de l'ordre stop loss / Création de limit + stop loss
    #72 ajout d'un OrderManager par exchange
    #73 Écriture des exceptions dans le fichier de log
    #76 refactorisation de la gestion des classes utilitaires avancées
    #83 Création de CONTRIBUTING.md
    #85 templates de tickets


# Nouvelles fonctionnalités :
    - Advanced Manager
    - Order Manager
    - Disponibilité des devises du portefeuille
    - Mesure de la rentabilité du portefeuille

# Correction de bugs :
    - Correction des notifications twitter
    - Correction des notifications gmail
    - Correction de l'évaluateur de bougie lorsqu'aucun pattern n'est détecté
    - Correction de la création des évaluateurs RealTime

Changelog pour 0.0.6-alpha
====================
*Date de sortie : 16 avril 2018*

# Tickets concernés :
    #15 correction de l'évaluateur bollinger
    #24 Ajout des tweets suivis sur twitter
    #35 première implémentation de l'évaluateur de bougie courante
    #63 analyse de divergence
    #66 Gestion des versions / changelog


# Nouvelles fonctionnalités :
    - Services modulaires
    - Service Dispatcher (producteur / client)
    - Sentiment Analyser

# Correction de bugs :
    - Correction de l'encodage twitter
    - Correction des évaluateurs twitter et google news
    - Correction de l'analyseur bollinger


Changelog pour 0.0.5-alpha
====================
*Date de sortie : 12 avril 2018*

# Tickets concernés :
    #54 initialisation des loggers avec uniquement les noms de classes
    #55 [EvaluatorCreator] déplacement des setters/getters du evaluator creator vers l'évaluateur
    #56 [Portfolio][update_portfolio] ajout des frais dans la partie devise
    #57 correction de la documentation
    #58 suppression du thread permanent dans l'évaluateur final
    #59 [Strategy] Création de la pertinence TA par timeframe
    #61 [Evaluators] Initialisation de la note d'évaluation avec une chaîne de caractères pour produire une exception

# Nouvelles fonctionnalités :
    - Ajout d'un webhook twitter simple
    - Implémentation de la notification twitter

# Correction de bugs :
    - Correction du contenu de la notification par mail
    - Correction de la notification twitter
    - Correction du finalize lors de la notification
