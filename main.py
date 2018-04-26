from bot import CryptoBot

if __name__ == '__main__':
    bot = CryptoBot()
    bot.create_exchange_traders()
    bot.create_evaluation_threads()
    bot.start_threads()
    bot.join_threads()
