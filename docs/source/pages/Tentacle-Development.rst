Tentacle development
===============================

About Tentacles
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This page covers tentacle development.

A tentacle is part of a `tentacle package <Tentacle-Package-Development.html>`_ and defines a tool for OctoBot
such as a way to analyse moving averages, listen to twitter for create grid-like orders.

OctoBot uses tentacles to handle:

* Price technical analysis (moving averages, RSI, MACD, ...)
* Social analysis (Twitter, Telegram, Reddit and Google)
* Evaluator signals interpretations (strategies)
* Orders creation and followup (trading modes)
* User interfaces and notifications (web, telegram, twitter)
* Backtesting data files reading and writing (.data)
* Exchanges fixes (to handle exchange local differences)

There is no limit to the things OctoBot can handle: everything that can be coded can be used by OctoBot through a
tentacle. It is possible to create a new tentacle to add a new tool to OctoBot or to build on an existing one and
improve it.


Developing a new Tentacle
-------------------------------------

The most efficient way to create a new tentacle si to build on top of an existing one to add features to it.
It is of course also possible to create a new completely new tentacle, in this case please have a look at similar
tentacles.

To create a tentacle improving an existing one, all you need to do, is to use the existing tentacle folder as a template
(to create a `tentacle package <Tentacle-Package-Development.html>`_) and
extend the existing tentacle you want to improve and re-implement the methods you want to change in the package's
python file.

Examples:

**TwitterNewsEvaluator** is a simple Twitter evaluator available by default in ``tentacles/Evaluator/Social/new_evaluator/news.py``.
Let's say you want to implement **SuperTwitterNewsEvaluator** which is a better Twitter evaluator.

Create the ``tentacles/Evaluator/Social/super_new_evaluator/`` `tentacle package <Tentacle-Package-Development.html>`_
based on ``tentacles/Evaluator/Social/new_evaluator`` and start coding the the python file.

.. code-block:: python


    import tentacles.Evaluator.Social as Socials

    class SuperTwitterNewsEvaluator(Socials.TwitterNewsEvaluator):
        # _get_tweet_sentiment is the TwitterNewsEvaluator method taking a tweet and
        # returning a number representing the "bullishness" of the tweet.
        # to change this part only, just redefine this method here
        def _get_tweet_sentiment(self, tweet, tweet_text, is_a_quote=False):
            # your new content
           sentiment = 1
           # some advanced tweet analysis to set sentiment value
           return sentiment

**SimpleStrategyEvaluator** is a strategy available by default in ``tentacles/Evaluator/Strategies/mixed_strategies_evaluator/mixed_strategies.py``.
Create the ``tentacles/Evaluator/Social/super_simple_strategy_evaluator/`` `tentacle package <Tentacle-Package-Development.html>`_
based on ``tentacles/Evaluator/Strategies/mixed_strategies_evaluator`` and start coding the the python file.

.. code-block:: python


    import tentacles.Evaluator.Strategies as Strategies

    class SuperSimpleStrategyEvaluator(SimpleStrategyEvaluator):

       # _trigger_evaluation is the methods called when OctoBot is
       # asking for a strategy evaluation
       async def matrix_callback(self,
                                 matrix_id,
                                 evaluator_name,
                                 evaluator_type,
                                 eval_note,
                                 eval_note_type,
                                 exchange_name,
                                 cryptocurrency,
                                 symbol,
                                 time_frame):
           final_evaluation = 0
           # some advanced computations to set final_evaluation value

           # update self.eval_note to store the strategy result
           self.eval_note = final_evaluation
           # finally, call self.strategy_completed to notify that
           # trading modes should wake up after this update
           await self.strategy_completed(cryptocurrency, symbol)
