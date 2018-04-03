from bot import Crypto_Bot

if __name__ == '__main__':
    bot = Crypto_Bot()
    bot.create_evaluation_threads()
    bot.start_threads()
    bot.join_threads()