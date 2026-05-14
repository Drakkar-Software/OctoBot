---
title: Trading
description: Vue d'ensemble du package octobot_trading — le moteur de trading central pour la connectivité aux exchanges, la gestion des ordres, le suivi du portefeuille et l'abstraction des trading modes.
sidebar_position: 1
---

# Package Trading

`octobot_trading` est le moteur de trading central. Il est responsable de tout ce qui se situe entre un appel d'API d'exchange brut et un ordre exécuté : connectivité aux exchanges, ingestion des données de marché, cycle de vie des ordres, suivi du portefeuille et couche d'abstraction de stratégie sur laquelle les trading modes se construisent.

## Gestion des exchanges

Chaque exchange connecté reçoit un `ExchangeManager`, l'objet racine qui relie entre eux les connecteurs, les traders et les data managers. Des indicateurs de mode sur cet objet contrôlent quels chemins de code s'activent, de sorte que la même logique de trading mode s'exécute de manière identique dans les contextes live, simulé et backtesting sans branchement.

`ExchangeBuilder` est le seul chemin de construction pris en charge. Il résout le trading mode actif, enregistre le manager dans un registre global singleton et démarre tous les sous-systèmes dans le bon ordre. Un cache de marché partagé évite les requêtes REST redondantes lorsque plusieurs instances d'exchange référencent le même marché.

Le connecteur de production encapsule ccxt et normalise toutes les réponses via une couche d'adaptateur, convertissant les exceptions ccxt en types internes. Les tentacles spécifiques aux exchanges sous-classent le connecteur REST pour surcharger le parsing ou exposer des points de terminaison supplémentaires. Pour le backtesting, un connecteur de simulateur rejoue les données depuis des importeurs au lieu de solliciter l'exchange.

## Données de marché

Chaque type de donnée — bougies, tickers, carnet d'ordres, trades, funding — suit le même pattern manager/canal/updater. Les managers conservent un état en mémoire, les canaux diffusent les mises à jour via async_channel, et les updaters tirent depuis REST ou poussent via WebSocket. La bascule entre l'interrogation REST et le WebSocket est transparente pour tout ce qui consomme le canal.

Les bougies sont stockées sous forme de buffer circulaire, trois mille entrées par time frame. Le mark price se résout à partir de quatre sources possibles avec repli automatique. Les composants peuvent enregistrer des callbacks de seuil de prix sur le flux du mark price ; c'est ainsi que les ordres stop-loss et take-profit simulés détectent que leur condition d'exécution est atteinte sans interrogation.

L'exchange n'est considéré comme prêt qu'une fois qu'un ensemble défini de topics de canaux a produit sa première mise à jour. Les exchanges de futures requièrent des signaux supplémentaires — positions, contrats, taux de funding — avant que l'indicateur de disponibilité ne soit positionné, ce qui empêche les stratégies d'agir sur un état incomplet.

## Ordres et portefeuille

Les ordres portent un UUID interne stable aux côtés de l'identifiant attribué par l'exchange. Ils prennent en charge les ordres chaînés qui s'auto-soumettent à l'exécution, les groupes d'ordres pour coordonner take-profit et stop-loss, les profils de prix trailing, et les déclencheurs basés sur le prix qui maintiennent un ordre inactif jusqu'à ce qu'un seuil soit franchi. Les ordres ouverts sont plafonnés en nombre et sérialisés vers le stockage pour la récupération au redémarrage.

La comptabilité du portefeuille utilise des verrous asynchrones et maintient des réservations de fonds — les fonds sont verrouillés à la création de l'ordre et libérés à l'exécution ou à l'annulation. Lorsque plusieurs trading modes partagent un même exchange, des sous-portefeuilles cloisonnent la comptabilité pour que chaque mode opère sur sa propre tranche. La conversion de valeur vers un marché de référence permet un suivi cohérent de la rentabilité entre actifs.

Les positions de futures se déclinent en deux variantes structurelles — linéaire/margée en quote et inverse/margée en base — avec des calculs de PnL et de marge différents. Les trades sont des enregistrements d'exécution immuables ; les transactions couvrent les frais, les événements de PnL, les dépôts, les retraits et les transferts, avec une protection contre l'insertion en double pour gérer la re-livraison par l'exchange.

## Trading modes

Les trading modes définissent la couche d'abstraction de stratégie. Un canal de mode transporte les signaux de marché depuis les producteurs — qui s'abonnent aux mises à jour de la matrice d'évaluateurs ou aux événements de clôture de bougie — vers les consommateurs qui traduisent ces signaux en opérations d'exchange. La séparation entre producteur et consommateur est ce qui permet à la même logique d'évaluation de piloter différents comportements d'ordres.

Les trading modes scriptés autorisent des scripts Python définis par l'utilisateur avec rechargement à chaud. Un objet de contexte agrège l'exchange manager, le symbole, le time frame et la bougie déclencheuse en une seule poignée. Un DSL intégré couvre la traduction de montants, le calcul de décalage de prix et l'inspection de position. Un script déclare en amont les flux de bougies dont il a besoin afin que le framework les active avant le premier appel du script.

## Signaux et stockage

Le système de signaux permet à un OctoBot de diffuser des opérations d'ordres sous forme de bundles structurés pour que des suiveurs les répliquent. Les signaux capturent l'intégralité du graphe de dépendances des ordres — ordres chaînés, groupes, déclencheurs — et utilisent un dimensionnement relatif au portefeuille afin que les suiveurs s'adaptent à leur propre portefeuille plutôt que de copier des quantités absolues.

Le stockage des ordres sérialise le graphe complet en mémoire, y compris les groupes, les chaînes, les profils trailing et les déclencheurs. Au démarrage, toutes les valeurs sont reconstruites avec la précision Decimal restaurée depuis des chaînes de caractères afin d'éviter la dérive en virgule flottante accumulée pendant la sérialisation. Un stockage historique optionnel enregistre chaque changement de statut d'ordre plutôt que seulement l'état terminal.
