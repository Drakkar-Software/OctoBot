.. role:: raw-html-m2r(raw)
   :format: html


Troubleshoot
============

Windows
-------

Time synchronization
^^^^^^^^^^^^^^^^^^^^

This issue happens when error messages such as ``'recvWindow' must be less than ...`` appear.

Open an administrator terminal and type:

.. code-block:: bash

   net stop w32time
   net start w32time
   w32tm /resync
   w32tm /query /status

Code from `serverfault.com <https://serverfault.com/questions/294787/how-do-i-force-sync-the-time-on-windows-workstation-or-server>`_

Another solution found by @alpi on discord channel : `timesynctool.com <http://www.timesynctool.com>`_

OctoBot freeze
^^^^^^^^^^^^^^

When running OctoBot on Windows, clicking into the OctoBot terminal (Powershell or Cmd) can freeze the log output and therefore freeze OctoBot execution (OctoBot will be waiting for the log to be published to continue).

To fix this issue, untick the "QuickEdit Mode" in your terminal properties and restart it.


.. image:: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/powerShellEditMode.jpg
   :width: 400 px
   :target: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/powerShellEditMode.jpg
   :alt: Powershell


.. image:: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/cmdQuickEdit.jpg
   :width: 400 px
   :target: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/cmdQuickEdit.jpg
   :alt: Cmd


To open the properties menu, right click on the terminal window header and select "properties".

Web interface display issue "MIME type ('text/plain') is not executable"
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If the web interface is now correctly displayed and this error (or similar) appears in your browser console: ``Refused to execute script from '<URL>' because its MIME type ('text/plain') is not executable, and strict MIME type checking is enabled.``\ , then there might be an issue with your Windows registry. Here is how to solve it:

#. Type ``regedit`` in the windows start menu
#. Go to ``\HKEY_CLASSES_ROOT``
#. Check the 2 following key values (they should be somewhat similar to these):

   .. image:: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/regedit-js.png
      :target: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/regedit-js.png
      :alt: regedit js


   .. image:: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/regedit-css.png
      :target: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/regedit-css.png
      :alt: regedit js

#. Check the the following key value in ``\HKEY_CLASSES_ROOT\MIME\Database\Content Type``

   .. image:: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/regedit-json.png
      :target: https://raw.githubusercontent.com/Drakkar-Software/OctoBot/assets/wiki_resources/regedit-json.png
      :alt: regedit js

#. Restart you OctoBot and reload the full page including cached files (CTRL+F5 or SHIFT+F5 depending on the browser)

Linux
-----

Time synchronization
^^^^^^^^^^^^^^^^^^^^

This issue happens when error messages such as ``'recvWindow' must be less than ...`` appear.

On Debian or Ubuntu, open a terminal and type:

.. code-block:: bash

   sudo service ntp stop
   sudo ntpd -gq
   sudo service ntp start

Requires ``ntp`` package installation ``sudo apt-get install ntp``.

Code from `askubuntu.com <https://askubuntu.com/questions/254826/how-to-force-a-clock-update-using-ntp#256004>`_.

Installation
^^^^^^^^^^^^

During pip install if you have SSL problems, open a terminal and type

.. code-block:: bash

   pip3 install service_identity --force --upgrade
