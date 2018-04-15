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
