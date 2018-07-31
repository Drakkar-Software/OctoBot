import logging
import os
import subprocess
import sys
import threading

from git import Repo, InvalidGitRepositoryError

from backtesting.collector.data_collector import DataCollector
from config.config import encrypt
from config.cst import ORIGIN_URL, GIT_ORIGIN
from tools.tentacle_creator.tentacle_creator import TentacleCreator
from tools.tentacle_manager.tentacle_manager import TentacleManager


class Commands:
    @staticmethod
    def update(logger, catch=False):
        logger.info("Updating...")
        try:
            try:
                repo = Repo(os.getcwd())
            except InvalidGitRepositoryError:
                logger.error("Impossible to update if OctoBot. "
                             "This error can appear when OctoBot's folder is not a git repository.")
                return
            # git = repo.git

            # check origin
            try:
                origin = repo.remote(GIT_ORIGIN)
            except Exception:
                origin = repo.create_remote(GIT_ORIGIN, url=ORIGIN_URL)

            if origin.exists():
                # update
                for fetch_info in origin.pull():
                    print(f"Updated {fetch_info.ref} to {fetch_info.commit}")

                # checkout
                # try:
                #     git.branch(VERSION_DEV_PHASE)
                # except Exception:
                #     repo.create_head(VERSION_DEV_PHASE, origin.refs.VERSION_DEV_PHASE)

                logger.info("Updated")
            else:
                raise Exception("Cannot connect to origin")
        except Exception as e:
            logger.info(f"Exception raised during updating process... ({e})")
            if not catch:
                raise e

    @staticmethod
    def check_bot_update(logger, log=True):
        try:
            repo = Repo(os.getcwd())
        except InvalidGitRepositoryError:
            logger.warning("Impossible to check if OctoBot is up to date. "
                           "This error can appear when OctoBot's folder is not a git repository.")
            return True

        try:
            diff = list(repo.iter_commits(f'{repo.active_branch.name}..{GIT_ORIGIN}/{repo.active_branch.name}'))
            if diff:
                if log:
                    logger.warning("Octobot is not up to date, please use '-u' or '--update' to get the latest release")
                return False
            else:
                if log:
                    logger.info("Octobot is up to date :)")
                return True
        except Exception:
            if log:
                logger.warning("Octobot is not up to date, please use '-u' or '--update' to get the latest release")
            return False

    @staticmethod
    def data_collector(config, catch=False):
        data_collector_inst = None
        try:
            data_collector_inst = DataCollector(config)
            data_collector_inst.join()
        except Exception as e:
            data_collector_inst.stop()
            if not catch:
                raise e

    @staticmethod
    def package_manager(config, commands, catch=False):
        try:
            package_manager_inst = TentacleManager(config)
            package_manager_inst.parse_commands(commands)
        except Exception as e:
            if not catch:
                raise e

    @staticmethod
    def tentacle_creator(config, commands, catch=False):
        try:
            tentacle_creator_inst = TentacleCreator(config)
            tentacle_creator_inst.parse_commands(commands)
        except Exception as e:
            if not catch:
                raise e

    @staticmethod
    def exchange_keys_encrypter(catch=False):
        try:
            api_key_crypted = encrypt(input("ENTER YOUR API-KEY : ")).decode()
            api_secret_crypted = encrypt(input("ENTER YOUR API-SECRET : ")).decode()
            print(f"Here are your encrypted exchanges keys : \n "
                  f"\t- API-KEY : {api_key_crypted}\n"
                  f"\t- API-SECRET : {api_secret_crypted}\n\n"
                  f"Your new exchange key configuration is : \n"
                  f'\t"api-key": "{api_key_crypted}",\n'
                  f'\t"api-secret": "{api_secret_crypted}"\n')
        except Exception as e:
            if not catch:
                logging.error(f"Fail to encrypt your exchange keys, please try again ({e}).")
                raise e

    @staticmethod
    def start_strategy_optimizer(config, commands):
        from backtesting.strategy_optimizer.strategy_optimizer import StrategyOptimizer
        optimizer = StrategyOptimizer(config, commands[0])
        if optimizer.is_properly_initialized:
            optimizer.find_optimal_configuration()
            optimizer.print_report()

    @staticmethod
    def start_bot(bot, logger, catch=False):
        try:
            # try to init
            bot.create_exchange_traders()
            bot.create_evaluation_threads()

            # try to start
            bot.start_threads()
            bot.join_threads()
        except Exception as e:
            logger.exception(f"OctoBot Exception : {e}")
            if not catch:
                raise e
            Commands.stop_bot(bot)

    @staticmethod
    def stop_bot(bot):
        bot.stop_threads()
        os._exit(0)

    @staticmethod
    def start_new_bot(args=""):
        python_command = f"{os.getcwd()}/start.py "
        command_args = "--pause_time=3"
        subprocess.Popen([sys.executable, python_command, command_args, args])

    @staticmethod
    def restart_bot(bot, args=""):
        start_new_bot_thread = threading.Thread(target=Commands.start_new_bot, args=(args,))
        start_new_bot_thread.start()
        start_new_bot_thread.join()
        Commands.stop_bot(bot)
