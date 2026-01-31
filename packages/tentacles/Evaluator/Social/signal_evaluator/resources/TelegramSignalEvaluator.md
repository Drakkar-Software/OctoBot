Very simple evaluator designed to be an example for an evaluator using Telegram signals.

Triggers on a Telegram signal from any group or channel listed in this evaluator configuration in which 
your Telegram bot is invited.

Signal format for this implementation is: **SYMBOL[evaluation]**. Example: **BTC/USDT[-0.45]**.

SYMBOL has to be in current watched symbols (in configuration) and evaluation must be between -1 and 1. 

Remember that OctoBot can only see messages from a
chat/group where its Telegram bot (in OctoBot configuration) has been invited. Keep also in mind that you
need to disable the privacy mode of your Telegram bot to allow it to see group messages.

See [OctoBot docs about Telegram interface](https://www.octobot.cloud/en/guides/octobot-interfaces/telegram?utm_source=octobot&utm_medium=dk&utm_campaign=regular_open_source_content&utm_content=telegramSignalEvaluator) for more information.
