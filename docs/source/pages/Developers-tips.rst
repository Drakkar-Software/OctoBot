Developer tips
==============

Cython
------

Compile in debug
^^^^^^^^^^^^^^^^

.. code-block:: shell

   make clean
   export CYTHON_DEBUG=true
   python setup.py build_ext --inplace

Debugging cythonized code
^^^^^^^^^^^^^^^^^^^^^^^^^

Run your python program with cython debugger :

.. code-block:: shell

   cygdb . -- --args python3-dbg test.py

Backtesting data
----------------

Backtesting data files are sqlite database files. When using the regular data collector, these files contain every historical candles the requested exchange is willing to give. You can use a `SQLite browser <https://sqlitebrowser.org/>`_ to explore these files.

Pytest
------

Fatal Python error: Segmentation fault
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


* Compile the package in debug
* Run tests with ``test.py`` :

.. code-block:: python

    import pytest

    if **name** == '\ **main**\ ':
        pytest.main(["tests"])

and
.. code-block:: shell

   cygdb . -- --args python3-dbg test.py

Strategy tests
--------------

To quickly check tentacles strategy tests states or develop a new tentacles strategy test, change the following lines
in **octobot/tests/functional_tests/strategy_evaluators_tests/abstract_strategy_test.py**\ :

.. code-block:: python

   def _handle_results(self, independent_backtesting, profitability):
       exchange_manager_ids = get_independent_backtesting_exchange_manager_ids(independent_backtesting)
       for exchange_manager in get_exchange_managers_from_exchange_ids(exchange_manager_ids):
           _, run_profitability, _, market_average_profitability, _ = get_profitability_stats(exchange_manager)
           actual = round(run_profitability, 3)
           # uncomment this print for building tests
           # print(f"results: rounded run profitability {actual} market profitability: {market_average_profitability}"
           #       f" expected: {profitability} [result: {actual ==  profitability}]")
           assert actual == profitability

into

.. code-block:: python

   def _handle_results(self, independent_backtesting, profitability):
       exchange_manager_ids = get_independent_backtesting_exchange_manager_ids(independent_backtesting)
       for exchange_manager in get_exchange_managers_from_exchange_ids(exchange_manager_ids):
           _, run_profitability, _, market_average_profitability, _ = get_profitability_stats(exchange_manager)
           actual = round(run_profitability, 3)
           # uncomment this print for building tests
           print(f"results: rounded run profitability {actual} market profitability: {market_average_profitability}"
                 f" expected: {profitability} [result: {actual ==  profitability}]")
           # assert actual == profitability

This will not stop tests on failure and display the current tests results as well as expected values.
