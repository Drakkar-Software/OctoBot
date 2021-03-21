OctoBot is customizable !
=========================

You can easily create or add existing tentacles to your OctoBot.

Tentacles are evaluators (using social media, trend analysis, news, ...), strategies (interpretations of evaluator's evaluations), analysis tools (implementation of a bollinger bands in depth analysis, twitter posts reader, ...) and trading modes.


.. image:: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/tentacles.jpg
   :target: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/tentacles.jpg
   :alt: tentacles


OctoBot is available for free with `basic implementations of a lot of different evaluators <https://github.com/Drakkar-Software/OctoBot-Tentacles>`_. The very high modularity in OctoBot's architecture allows it to automatically look for the most advanced version(s) of all the available tentacles and automatically use them in its trading strategies.

Therefore, anyone can implement its own version of any evaluator, strategy, analysis tool and trading modes. It's even possible to use another version provided by someone else !

Tentacle installation (OctoBot v0.4)
------------------------------------

Default tentacles
^^^^^^^^^^^^^^^^^

OctoBot default tentacles are automatically installed when first starting your OctoBot.

You can re-install them anytime using the following command options to your OctoBot binary or python version:
``tentacles --install --all``

It is also possible to install a tentacles package using the web interface Tentacles tab.

Installing a tentacles
^^^^^^^^^^^^^^^^^^^^^^

To install tentacles, OctoBot can either install a tentacle package (zipped bundle of tentacles) or a single tentacle from a local folder.

Tentacle packages
~~~~~~~~~~~~~~~~~

To install a package, use the following options:
``tentacles --install --all --location "path/to/your/package/package_name.zip"``

To create a tentacles package from a local folder:


#. Make sure it follows the `OctoBot-Tentacles folder architecture <https://github.com/Drakkar-Software/OctoBot-Tentacles>`_
#. Call OctoBot with the following options: ``tentacles -p "path/to/your/packed/tentacles/pack_name.zip" -d "path/to/your/local/tentacles/folder"``

Once your package is created, you can install it using the ``tentacles --install --all --location "path/to/your/packed/tentacles/pack_name.zip"`` command. You can also make it available from an URL and later install it via: ``tentacles --install --all --location "https://my.tentacles.com/pack_name"`` for example.

Installing a tentacle package will replace any existing source file taht share the same name. It can be used to update sources without changing the version number.

Single tentacles
~~~~~~~~~~~~~~~~

It is also possible to install a single tentacle from a local folder using the following options: ``tentacles --single-tentacle-install "path/to/your/tentacle/to/install" Evaluator/TA``. Please note that in this command, you also need to provide the type of the tentacle (\ ``Evaluator/TA`` in this example) for OctoBot to know how to handle it.

Tentacle customization (OctoBot v0.3)
-------------------------------------

All you need to do, to improve a tentacle, is to extend the existing one you want to improve and re-implement the methods you want to change.

Examples:

.. code-block:: python

    #. **TwitterNewsEvaluator** is a simple Twitter evaluator available by default in ``tentacles/Evaluator/Social/Default/new_evaluator.py``. To improve it, all you need to do is to create a file, let's say ``advanced_twitter_news_evaluator.py`` containing a class extending the simple evaluator:

    from tentacles.Evaluator.Social import TwitterNewsEvaluator

    class AdvancedTwitterNewsEvaluator(TwitterNewsEvaluator):
        def __init__(self):
            super().__init__()

.. code-block:: python

   # let's say we want to change this method
   def get_tweet_sentiment(self, tweet):
       sentiment = 1
       # some advanced tweet analysis to set sentiment value
       return sentiment

**StatisticAnalysis** is a simple Statistic analysis tool available by default in ```tentacles/Evaluator/Util/Default/statistics_analysis.py```. To improve it, all you need to do is to create a file, let's say ```advanced_statistics_analysis.py``` containing a class extending the simple analyser:

.. code-block:: python

   from tentacles.Evaluator.Util import StatisticAnalysis


   class AdvancedStatisticAnalysis(StatisticAnalysis):

       # let's say we want to change this method
       @staticmethod
       def analyse_recent_trend_changes(data_frame, delta_function):
           changes = 1
           # some advanced trend change detection here
           return changes

**InstantSocialReactionMixedStrategiesEvaluator** is a simple strategy tool available by default in ``tentacles/Evaluator/Strategies/Default/mixed_strategies_evaluator.py``. To improve it, all you need to do is to create a file, let's say ``advanced_instant_strategy_evaluator.py`` containing a class extending the simple strategy:

.. code-block:: python


    from tentacles.Evaluator.Strategies import InstantSocialReactionMixedStrategiesEvaluator

    class AdvancedInstantSocialReactionMixedStrategiesEvaluator(InstantSocialReactionMixedStrategiesEvaluator):


       # eval_impl is the methods called when OctoBot is asking for a strategy evaluation
       async def eval_impl(self):
           final_evaluation = 0
           # some advanced computations to set final_evaluation value

           # finally, update self.eval_note to store the strategy result
           self.eval_note = final_evaluation

Manual installation
^^^^^^^^^^^^^^^^^^^

Only 3 steps are necessary to install a new tentacle:


#. Store the tentacle in the ``Advanced`` folder contained in the folder of the basic version of the tentacle
#. In this ``Advanced`` folder, create or update the ``__init__.py`` file to add the following line:
   .. code-block:: python

      from .file_containing_new_implementation_name import *

#. Add the class of your evaluator into your ``tentacles/Evaluator/evaluator_config.json`` or ``tentacles/Trading/trading_config.json`` file (depending on the type of tentacle) alongside the others. This will allow OctoBot to see it.

Examples with the tentacles created in the **Tentacle customization** section:


#. **TwitterNewsEvaluator** 


* Store the tentacle file: ``advanced_twitter_news_evaluator.py`` in ``tentacles/Evaluator/Social/Advanced``
* ``In tentacles/Evaluator/Social/Advanced``\ , create or edit the ``__init__.py`` file and add the following line:
  .. code-block:: python

     from .advanced_twitter_news_evaluator import *


#. **StatisticAnalysis** 


* Store the tentacle file: ``advanced_statistics_analysis.py`` in ``tentacles/Evaluator/Util/Advanced``
* ``In tentacles/Evaluator/Util/Advanced``\ , create or edit the ``__init__.py`` file and add the following line:
  .. code-block:: python

     from .advanced_statistics_analysis import *


#. **InstantSocialReactionMixedStrategiesEvaluator** 


* Store the tentacle file: ``advanced_instant_strategy_evaluator.py`` in ``tentacles/Evaluator/Strategies/Advanced``
* ``In tentacles/Evaluator/Strategies/Advanced``\ , create or edit the ``__init__.py`` file and add the following line:
  .. code-block:: python

     from .advanced_instant_strategy_evaluator import *

Advanced: Evaluator and Strategy creation (OctoBot v0.3)
--------------------------------------------------------

With OctoBot, everyone can create it's own evaluators and strategies, even if it's not already existing already in a simple version. 

In order to add a new type of evaluator, you need to respect the following rules:


* Evaluators extend any type of *implementation* of **RealTimeEvaluator**\ , **SocialEvaluator** or **TAEvaluator**

Example: RSIMomentumEvaluator extends *MomentumEvaluator* which extends **TAEvaluator**. Here RSIMomentumEvaluator is an evaluator extending **TAEvaluator**\ 's implementation *MomentumEvaluator*

In order to add a new type of strategy, you need to respect the following rules:


* Strategies extend any type of *implementation* of **StrategiesEvaluator**

Example: InstantSocialReactionMixedStrategiesEvaluator extends *MixedStrategiesEvaluator* which extends **StrategiesEvaluator**. Here InstantSocialReactionMixedStrategiesEvaluator is a strategy extending **StrategiesEvaluator**\ 's implementation *MixedStrategiesEvaluator*


* Evaluators and strategies have to implement all the ``@abstractmethod`` methods.
* Evaluators other than the ones extending **TAEvaluator** can be threaded, in this case ``self.is_threaded`` should be set to true. Strategies can't be threaded.
* Evaluators and strategies have to set ``self.eval_note`` to a value between -1 and 1 (-1 for buy and 1 for sell) to be considered.
* Evaluators are ignored if ``self.enabled`` is not set to true.
* Evaluators and strategy files have to be included in the ``__init__.py`` file using the following line: 
  ``from .evaluator_file import *``. 

Including a new evaluator or strategy will automatically tell OctoBot to load this evaluator or strategy.

Join the OctoBot community !
----------------------------

After creating your own evaluators, strategies, utilitary tools, or trading modes you can share them with the OctoBot community !

The OctoBot team will be delighted to add new tentacles to the project and update the `default OctoBot evaluation and strategies tentacles package <https://github.com/Drakkar-Software/OctoBot-Tentacles>`_ !
