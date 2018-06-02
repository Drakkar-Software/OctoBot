Changelog for 0.1.0_1-beta
====================
*Released date : June 2 2018*

# Bug fix :
    #201 [Real trading] Fix bug when loading exchange current order

Changelog for 0.1.0-beta
====================
*Released date : June 1 2018*

**Info** : 
- Config : "packages" root key renamed to "tentacles"

# Concerned issues :
    #108 [RoadMap] format RoadMap into an attractive image
    #109 [RoadMap] add RoadMap tracker on ReadMe.md
    #136 [Tests] Improve trading tests coverage
    #139 [Tests] Improve evaluator management tests coverage
    #156 [Documentation] Add documentation for evaluator management classes
    #163 [Exchanges Tests] implement web sockets for binance tests
    #164 [ReadMe] make readme sexy !
    #174 Renaming CryptoBot to Octobot
    #181 [Telegram] Pause and resume trading
    #183 Can't create order when order already on exchange on bot start
    #186 [Twitter Interface] Some notifications are not sent to Twitter website

# New features :
    - Telegram pause / resume trading
    - Beautiful README and logo
    - Create roadmap
    - Improve tests coverage

# Bug fix :
    - Fix negative portfolio in simulation

Changelog for 0.0.12-alpha
====================
*Released date : May 26 2018*

**Info** : 
- Config : "data_collector" root key removed
- Backtesting : "file" root key changed to "files" as array
- Package Manager : need to perform `python3 start.py -p install all` to install evaluators

# Concerned issues :
    #84 [Environment] Create docker
    #86 [CI] Implement third party
    #139 [Tests] Improve evaluator management tests coverage
    #144 [Bug] Investigate version 0.0.11 negative simulated portfolio
    #145 [Datacollector] Implements multiple symbol
    #146 [Backtesting] Implement multi symbols
    #147 [Backtesting] Implement multi exchanges
    #148 [Backtesting] Implement better order manager backtesting features
    #151 [Services] log info message when started
    #152 [Wiki] complete wiki version 1
    #153 [Beta Version] Prepare beta version
    #154 [Exchanges] implement web sockets for binance exchange
    #155 [TA] improve real time evaluator
    #157 [Exchanges] manage websockets availability in exchange manager
    #158 [Order management] implement order callback update for websockets additionnaly to poll updates
    #159 added cyclic log file management
    #160 [Real Trader] taking exchanges symbol and minimum trade requirements into account
    #161 [Evaluators] Allows in run evaluator creation
    #162 [Services] Allows in run service creation
    #163 [Exchanges Tests] implement web sockets for binance tests
    #165 Bump matplotlib from 2.0 to 2.2.2
    #166 [Tests] Features testing
    #171 [Package Manager] Prototype
    #172 [Telegram Interface] No response when ask profitability
    #175 Add tests for order creation
    #176 [Package manager] implement advanced evaluators

# New features :
    - Multi symbols / exchanges data collector
    - Multi symbols backtesting
    - Wiki completed
    - Websocket management
    - Exchange management
    - Binance Websocket
    - Cyclic logging
    - Evaluator & Service restarting management
    - Package Manager
    - Windows installer
    
# Bug fix :
    - Improve code quality
    - Fix exception in order update_status when backtesting
    - Fix order fill bug in simulation
    - Fix telegram no response on /profitability command
    - Taking exchanges symbol and minimum trade requirements into account


Changelog for 0.0.11-alpha
====================
*Released date : May 11 2018*

**Info** : 
- Config : "simulator" root key changed to "trader_simulator"

**Warning** : 
- <span style="color:red">Real trading is in pre-alpha version</span>

# Concerned issues :
    #87  [Interface] Prototype telegram interface
    #132 [Web]: add portfolio view
    #133 [Backtesting] Implement report 
    #134 [Order Creation] Fix negative quantity 
    #135 [Simulation] Fix order and trades manager 
    #136 [Tests] Improve trading tests coverage
    #138 [Trading] Implement real trades
    #139 prepare evaluators tests
    #140 [Trading] Implement real portfolio management
    #141 [Trading] Implement real order management
    #142 [Timeframe manager] Implementation

# New features :
    - Web interface improvements
    - Telegram interface
    - Telegram notifications
    - Pretty Printer tool
    - Eval note expiration management
    - Beginning of real trading implementation
    - Multiple new tests to improve code coverage
    - TimeFrame Manager
    
# Bug fix :
    - Fixed trader simulation order creation
    - [Order Creation] Fix negative quantity 

Changelog for 0.0.10-alpha
====================
*Released date : May 5 2018*

# Concerned issues :
    #63 Calculate evaluator divergence note 
    #86 [CI] Implement third party
    #117 auto adapt symbol configuration for backtesting 
    #119 TA test architecture
    #120 [Backtesting] Test Zipline lib implementation
    #121 added sudden pump data and described bank data 
    #122 added test_reaction_to_over_bought_then_dip to all TA 
    #123 added rise after over-sold test for all TA
    #124 added flat trend tests on all TA 
    #125 [Notification] Double notification when an order linked is cancelled
    #127 Add in price graph and out price graph indicator list plot 
    #126 [Order] Too much canceled orders when RealTime Evaluators are created
    #128 [Notification] No notification of profitability
    #129 [Web] Create web interface prototype 

# New features :
    - Web interface prototype
    - Full TA patterns tests
    - Data Visualiser
    - Performance Analyser
    - Bot starter with options
    - Multiple new tests to improve code coverage
    
# Bug fix :
    - Fix risk logic with market orders
    - Fix notifications : only concerned symbol
    - Fix default config
    - Fix datavisualiser style
    - Fix RedditEvaluator overriden method param names
    - Fix portfolio profitability notification 


Changelog for 0.0.9-alpha
====================
*Released date : Apr 30 2018*

# Concerned issues :
    #20 added reddit service and started reddit dispatcher 
    #22 added webpage news retreiver 
    #47 backtesting 
    #76 data collector
    #92 [Evaluators] Enable / disable with config file
    #102 added advanced evaluator in dispatcher handler
    #103 [Portfolio] Implement pytests last 
    #104 Exchange Manager
    #105 fix cancel notification
    #107 factorized refresher threads into one per symbol
    #113 Fix portfolio bug management

# New features :
    - Backtesting
    - Data Collector
    - Data Collector Parser
    - Exchange Manager
    - New social evaluator (reddit, twitter posted media & websites)
    - Tests implementation and coverage
    
# Bug fix :
    - Fix Portfolio management
    - Fix critical bug on symbol evaluator
    - Fix critical bug in order creation
    - Fix trader join
    - Fix tests
    - Fix real time constants
    - Fix new dependency raspberry install
    - Fix realtime instant fluctuation evaluator pending note
    - Fix notification style end order
    - Fix portfolio concurrency access
    
Changelog for 0.0.8-alpha
====================
*Released date : Apr 24 2018*

# Concerned issues :
    #26 optimized moving average evaluator 
    #90 added can_create_order() method to check if an order is issuable
    #91 refactored dispatchers
    #93 [Profitability] Fix calculation error
    #97 [Order] Fix order cancel when state change
    #99 [Symbol evaluator] Symbol evaluator fail to manage multi exchanges
    #100 [Exchanges] Implement automatic instanciation of exchange when keys are in config.json


# New features :
    - New TA evaluators : DoubleMA, BollingerBand, ADX, MACD
    - Risk trading management (order price, order quantity, final state thresholds)

# Bug fix :
    - Fix constants in order creation
    - Fix order end notification
    - Fix Limit price 10% to 5% max
    - Fix gmail notifications
    - Fix evaluator final & add startup notification
    - Fix portfolio profitability
    - Fix order cancel when state change
    
Changelog for 0.0.7-alpha
====================
*Released date : Apr 21 2018*

# Concerned issues :
    #26 added bollinger momentum and advanced util management
    #48 [Portfolio] Manage availability of currencies
    #51 [Trade / Trade Simulator] Implement profitability
    #68 Create Advanced list manager
    #69 fix availability and create mail notification profitability
    #70 [Trading Simulator] Manage stop loss order / Create limit + stop loss 
    #72 add OrderManager per exchange 
    #73 Write exception into log file
    #76 refactor advanced util classes management 
    #83 Create CONTRIBUTING.md
    #85 issue templates 


# New features :
    - Advanced Manager
    - Order Manager
    - Portfolio currencies availability
    - Portfolio profitability measurement

# Bug fix :
    - Fix twitter notifications
    - Fix gmail notifications
    - Fix candle evaluator when no pattern is detected
    - Fix RealTime Evaluators creation
    
Changelog for 0.0.6-alpha
====================
*Released date : Apr 16 2018*

# Concerned issues :
    #15 fixed bollinger evaluator
    #24 Add twitter followed tweets
    #35 first implementation of current candle evaluator
    #63 divergence analysis
    #66 Manage versions / changelog


# New features :
    - Modular Services
    - Service Dispatcher (producer / client)
    - Sentiment Analyser

# Bug fix :
    - Fix twitter encoding
    - Fix twitter and google news evaluators
    - Fix bollinger analyser


Changelog for 0.0.5-alpha
====================
*Released date : Apr 12 2018*

# Concerned issues :
    #54 initialized loggers with only class names
    #55 [EvaluatorCreator] move evaluator creator's setters/getters to evaluator
    #56 [Portfolio][update_portfolio] add fees in currency part
    #57 documentation fix
    #58 removed permanent thread in final evaluator
    #59 [Strategy] Create TA relevancy by timeframe
    #61 [Evaluators] Init eval note with string to produce an exception

# New features :
    - Added twitter simple webhook
    - Implement twitter notification

# Bug fix :
    - Fix mail notification content
    - Fix twitter notification
    - Fix finalize when notify
