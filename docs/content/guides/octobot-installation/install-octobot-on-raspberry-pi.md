---
title: "With Raspberry Pi"
description: "Learn how to easily install and start your OctoBot on Raspberry Pi using the executable version of the bot."
sidebar_position: 5
---



# Install OctoBot on Raspberry Pi

## 1. Preparing the Raspberry Pi

1. Install Rapberry OS and configure it.
2. Enable `ssh` as it will be essential for accessing the Raspberry remotely from a local network
3. Create a new user or use the default one and change the password to use a strong password.

## 2. Install OctoBot

1. On the Octobot latest release page, download the `OctoBot_linux_arm64`
   file: this is the Raspberry Pi x64 compatible version of OctoBot.

<div style="text-align: center">
  <a href="https://github.com/Drakkar-Software/OctoBot/releases/latest"><strong>Get the latest release</strong></a>
</div>

2. Copy the file to the `/home/pi/` folder  
   Note: here `pi` it is the folder of the `pi` user (default user).

3. To facilitate this process (when using Windows), you can use <a href="https://winscp.net/eng/index.php" rel="nofollow">WinSCP</a>: it has a graphical interface and works like the Windows "file explorer". It will also be easier to later edit your Raspberry Pi files.

4. Connect to Raspberry through a terminal using the following command: `ssh pi@192.168.1.XX` replace `pi` by your Raspberry username and `192.168.1.XX` by your Raspberry IP address and enter the password you created in setp 1.

5. After logging on to the Raspeberry it is necessary to make the file "OctoBot_linux_arm64" into an executable. To do this, still from the terminal, type this command: `sudo chmod +x OctoBot_linux_arm64`

6. Done. Nothing else is needed!

## 3. Run OctoBot

1. To run OctoBot, use the terminal from the previous step or open a new one and go to the folden containing the OctoBot executable and type in `./OctoBot_linux_arm64`  
   OctoBot starts and creates the necessary folders the first time it runs.

2. In the Web browser you already have access to your OctoBot through the Raspberry Pi's local IP at the following address: `http://192.168.1.XX:5001` where `192.168.1.XX` is the IP address of your Rapberry Pi. It is the same as the one you use to connect to your Rapberry Pi.

3. Press `Ctrl-A` then `Ctrl-D`. This will detach your screen session but leave your OctoBot process running. You can now close the terminal.

## 4. Starting OctoBot automatically

You might want OctoBot to start automatically when starting your Raspberry Pi.

To start OctoBot automatically after restarting Raspberry Pi, proceed as follows.  
Still from a terminal:

1. Type in the following command: `crontab -e`
2. Add the following line at the end: `@reboot /home/pi/OctoBot_linux_arm64` where `pi` is your username
3. Save

In the event of a power outage, your Raspberry Pi will automatically restart your OctoBot and continue executing its configured strategies.

Also, every time your Raspberry Pi starts up, it will run Octobot and you will be able to access it from your browser.
