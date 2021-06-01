OctoBot is customizable !
=========================

You can easily create or add existing tentacles to your OctoBot.

Tentacles are evaluators (using social media, trend analysis, news, ...), strategies (interpretations of evaluator's evaluations), analysis tools (implementation of a bollinger bands in depth analysis, twitter posts reader, ...) and trading modes.


.. image:: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/tentacles.jpg
   :target: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/tentacles.jpg
   :alt: tentacles


OctoBot is available for free with `basic implementations of a lot of different evaluators <https://github.com/Drakkar-Software/OctoBot-Tentacles>`_. The very high modularity in OctoBot's architecture allows it to automatically look for the most advanced version(s) of all the available tentacles and automatically use them in its trading strategies.

Therefore, anyone can implement its own version of any evaluator, strategy, analysis tool and trading modes. It's even possible to use another version provided by someone else !

Tentacle installation
------------------------------------

Default tentacles
^^^^^^^^^^^^^^^^^

OctoBot default tentacles are automatically installed when first starting your OctoBot.

You can re-install them anytime using the following command options to your OctoBot binary or python version:
``tentacles --install --all``

It is also possible to install a tentacles package using the web interface Tentacles tab.

Installing tentacles
^^^^^^^^^^^^^^^^^^^^^^

To install tentacles, OctoBot can either install a tentacle package (zipped bundle of tentacles) or a single tentacle from a local folder.

Tentacle packages
~~~~~~~~~~~~~~~~~

To install a package, use the following options:

.. code-block:: shell

    tentacles --install --all --location "path/to/your/package/package_name.zip"

To create a tentacles package from a local folder:


#. Make sure it follows the `OctoBot-Tentacles folder architecture <https://github.com/Drakkar-Software/OctoBot-Tentacles>`_
#. Call OctoBot with the following options:

.. code-block:: shell

    tentacles -p "path/to/your/packed/tentacles/pack_name.zip" -d "path/to/your/local/tentacles/folder"

Once your package is created, you can install it using the command :

.. code-block:: shell

    tentacles --install --all --location "path/to/your/packed/tentacles/pack_name.zip"

You can also make it available from an URL and later install it via (for example) :

.. code-block:: shell

    tentacles --install --all --location "https://my.tentacles.com/pack_name"

Installing a tentacle package will replace any existing source file taht share the same name. It can be used to update sources without changing the version number.

Single tentacles
~~~~~~~~~~~~~~~~

It is also possible to install a single tentacle from a local folder using the following options:

.. code-block:: shell

    tentacles --single-tentacle-install "path/to/your/tentacle/to/install" Evaluator/TA

Please note that in this command, you also need to provide the type of the tentacle (\ ``Evaluator/TA`` in this example) for OctoBot to know how to handle it.
