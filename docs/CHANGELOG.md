Changelog for 0.0.10
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


Changelog for 0.0.9
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
    
Changelog for 0.0.8
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
    
Changelog for 0.0.7
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
    
Changelog for 0.0.6
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


Changelog for 0.0.5
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
