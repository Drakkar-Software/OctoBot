.. role:: raw-html-m2r(raw)
   :format: html


Developer startup guide
===============================

Note: this page is referring to OctoBot in versions superior to 0.4.0.

Environment setup
-------------------------------

We recommand using `PyCharm <https://www.jetbrains.com/pycharm/>`_ to navigate through the OctoBot projects. This IDE will allow you to open and navigate through the multiple OctoBot repositories and make your OctoBot run setup use the code directly from the clonned repos using the project dependencies.

More details in the `OctoBot repositories <Developer-Guide.html#id1>`_ and `Setting up the recommended OctoBot development environment <Developer-Guide.html#id2>`_ sections.

OctoBot architecture
--------------------

Philosophy
^^^^^^^^^^

The goal behind OctoBot is to have a **very fast and scalable** trading robot.

To achieve this, OctoBot is entirely built around the `asyncio <https://docs.python.org/3/library/asyncio.html>`_ producer-consumer `Async-Channel <https://github.com/Drakkar-Software/Async-Channel>`_ framework which allows to very quickly and efficiently transmit data to different elements within the bot. The idea is all the time maintain **fully up-to-date data** without having to use update loops (that require have inefficient sleeping time) while also **waking up the evaluation chain as quickly as possible** when an update is available (without having to wait for any update cycle of any update loop).

Additionally, in order to save CPU time, as little threads as possible are use by OctoBot (usually less than 10 with a standard setup).

As a final touch, each CPU or memory intensive task is further optimized using `Cython <https://cython.org/>`_. The python code of these tasks is translated into highly optimized C code that allows for less instructions to process and optimized memory representation ending up with a huge performance increase.

Overview
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The OctoBot code is split into `several repository <Developer-Guide.html#id1>`_. Each module is handled as an independent python module and is available on the `official python package repository <https://pypi.org/>`_ (used in ``pip`` commands). Modules are made available as python source modules as well as as compiled modules which includes cython optimizations. Installing a module on a platform which as not already been built and made available on `pypi.org <https://pypi.org/>`_ will take much more time as ``pip`` will cythonize and compile the given module, which also requires a cpp compiler.

OctoBot
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


.. image:: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/octobot_arch.svg
   :target: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/octobot_arch.svg
   :alt: OctoBot architecture

Simplified view of the OctoBot core components.

Note: Inside the OctoBot part, each arrow is an async channel.

OctoBot tentacles
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Tentacles are OctoBot's extensions, they are meant to be easily customizable, can be activated or not and do any specific action within OctoBot.

Evaluation chain tentacles
~~~~~~~~~~~~~~~~~~~~~~~~~~

They are tools to analyze market data as well as any other type of data (twitter, telegram, etc). They implement abstract evaluators, strategies and trading modes.

Utility tentacles
~~~~~~~~~~~~~~~~~

These are OctoBot's interfaces (web, telegram), notification systems, social news feeds and backtesting data collectors. They implement abstract interfaces, services, service feeds, notifiers and data collectors

Evaluators, strategies and trading modes:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Evaluators
~~~~~~~~~~

Simple python classes that will automatically be wake up when new data is available. Their goal is to set ``self.eval_note`` and call ``await self.evaluation_completed`` that will then be made available to the Strategy(ies). They should be dedicated to a single simple task such as (for example) evaluate the RSI on the current data or looks for a divergence in a trend.

Strategies
~~~~~~~~~~

Strategies are more complex elements, they can read all the evaluators evaluations on every time frame and are considering these evaluations to set their ``self.eval_note`` and call ``await self.strategy_completed``. As a comparison if evaluators are human senses, strategies are the brain that will take these senses' signals and decide to do something or not. Strategies can be generic like SimpleStrategyEvaluator that will take any standard evaluator and time frame into account or using specific evaluators only like MoveSignalsStrategyEvaluator.

Trading modes
~~~~~~~~~~~~~

Trading modes use the strategy(ies) evaluations to create, update or cancel orders. Using the strategies signals, they are responsible for the way to translate a signal into an order by looking at the available funds, open orders, considering stop loss or not and other trading related responsibilities.

Triggers
~~~~~~~~

Evaluators, strategies and trading modes are automatically triggered when their channel has a new data. Trigger sources are:

For evaluators


* Technical evaluators: any new candle or refresh request (with updated candles data) from a strategy
* Real time evaluators: any new candle and any market price change
* Social evaluators: associated signal (ex: a tweet for a twitter social evaluator)

For strategies


* After a technical evaluator cycle: when all TA have updated their evaluation and called ``await self.evaluation_completed``
* After any real time evaluator evaluation and call of ``await self.evaluation_completed``
* After any social evaluator evaluation and call of ``await self.evaluation_completed``

For trading mode


* After any strategy evaluation and call of ``await self.strategy_completed``

OctoBot repositories
--------------------

OctoBot code is split in multiple repositories:


* https://github.com/Drakkar-Software/OctoBot (dev branch) for the main program initialization, backtesting and strategy optimizer setup as well as community data management.
* https://github.com/Drakkar-Software/OctoBot-Tentacles (dev branch) for tentacles: evaluators, strategies, trading modes, interfaces, notifiers, external data feeds (twitter, telegram etc), backtesting data formats management and exchange specific behaviors.
* https://github.com/Drakkar-Software/OctoBot-Trading for everything trading and exchange related: exchange connections, exchange data fetch and update, orders, trades and portfolios management.
* https://github.com/Drakkar-Software/OctoBot-evaluators for everything related to evaluators and strategies. 
* https://github.com/Drakkar-Software/OctoBot-Services for everything related to interfaces: graphic (web) and text(telegram), notifications push and social analysis data management: update engine to handle new data from an external feed (ex: twitter) when it gets available.
* https://github.com/Drakkar-Software/OctoBot-Backtesting for the backtesting engine and scheduling as well as historical data collection unified storage management.
* https://github.com/Drakkar-Software/OctoBot-Tentacles-Manager for tentacles installation, updates and interactions: get a tentacle documentation, configuration or it's dependencies.
* https://github.com/Drakkar-Software/OctoBot-Commons for common tools and constants used across each above repository.
* https://github.com/Drakkar-Software/Async-Channel which is used by OctoBot as a base framework for every data transfer within the bot. This allows a highly optimized and scalable architecture that adapts to any system while using a very low amount of CPU and RAM.

Setting up the recommended OctoBot development environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Requirements:


* IDE: `PyCharm <https://www.jetbrains.com/pycharm/>`_
* SCM: `Git <https://git-scm.com/downloads>`_\ , we also use `GitKraken <https://www.gitkraken.com/git-client>`_ to easily manage OctoBot's multiple repos, this is just a quality of life improvement and is not necessary.
* Language: `Python 3.8 <https://www.python.org/downloads/>`_


#. Clone each `OctoBot repository <Developer-Guide.html#id1>`_ using the dev branch when specified.
#. Open Pycharm and open the OctoBot repository.
#. Open every other `OctoBot repository <Developer-Guide.html#id1>`_ alongside to the main OctoBot repository **in the same PyCharm window**.
#. In File/Settings/Project/Python Interpreter: select your installed python3.8 and create a new virtual environment through PyCharm.

   .. image:: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/python_interpreter.png
      :target: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/python_interpreter.png
      :alt: python interpreter

#. In File/Settings/Project/Python Dependencies: For each repository: check its required OctoBot repository dependency. This will allow your PyCharm python runner to use your OctoBot repositories as source code directly. Thanks to this you will be able to edit any file in any repo and it will be taken into account in your other PyCharm run profiles runners from other open OctoBot repo. This is useful when running tests. If you skip this, you will need to install every OctoBot module with pip and won't be able to edit their code.

   .. image:: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/python_dependencies.png
      :target: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/python_dependencies.png
      :alt: python dependencies

#. For each OctoBot's repository: install missing dependencies in requirements.txt and dev_requirements.txt. **Warning** do not install the requirements related to the previously downloaded repositories or your python runner will use them instead of your local code version.
#. Create PyCharm run configurations using the previously created virtual env (with all the dependencies installed) for each way you want to start python commands (running OctoBot, running tests, etc). Example of run configs (only the selected one is necessary to start OctoBot):

   .. image:: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/run_config.png
      :target: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/run_config.png
      :alt: run configuration

#. You can now run and debug the whole OctoBot project and its repositories.

A script to install these git repo on a unix setup

.. code-block:: bash

   #!/bin/bash

   readonly REMOTE_DEVBRANCH="remotes/origin/dev"
   readonly DEVBRANCH="dev"
   readonly BASEDIR=$(dirname "$0")

   branch_work() {
     dir=$1
     devbranch=$2
     branch=$(cd $BASEDIR/$dir && git name-rev --name-only HEAD)
     if $devbranch; then
       if [ $branch == $REMOTE_DEVBRANCH ]; then
         echo "[WARN] Already on branch: $branch "
         echo "[INFO] Delete Folder: $dir - if you would like to have clean $dir project"
       else
         (cd $dir; git checkout $DEVBRANCH)
       fi
     fi
   }

   project_work() {
     url=$1
     devbranch=$2
     dir=$(basename -s .git "$url")
     echo "Check Dir $BASEDIR/$dir"
     if [ -d $BASEDIR/$dir ]; then
       echo "[WARN] Directory: $dir exists!"
       branch_work $dir $devbranch
     else
       echo "----- $dir -----"
       git clone $url
       branch_work $dir $devbranch
       echo "----- END $dir -----"
     fi
   }

   #Uses dev branch: true/false
   project_work https://github.com/Drakkar-Software/OctoBot.git true
   project_work https://github.com/Drakkar-Software/OctoBot-Tentacles.git true
   project_work https://github.com/Drakkar-Software/OctoBot-Trading false
   project_work https://github.com/Drakkar-Software/OctoBot-evaluators false
   project_work https://github.com/Drakkar-Software/OctoBot-Services false
   project_work https://github.com/Drakkar-Software/OctoBot-Backtesting false
   project_work https://github.com/Drakkar-Software/OctoBot-Tentacles-Manager false
   project_work https://github.com/Drakkar-Software/OctoBot-Commons false
   project_work https://github.com/Drakkar-Software/Async-Channel false

*Thanks for reading this guide and if you have any idea on how to improve it, please reach out to us !*
