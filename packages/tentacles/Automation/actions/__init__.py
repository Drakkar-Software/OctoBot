from octobot_tentacles_manager.api.inspector import check_tentacle_version
from octobot_commons.logging.logging_util import get_logger

if check_tentacle_version('1.2.0', 'stop_trading_action', 'OctoBot-Default-Tentacles'):
    try:
        from .stop_trading_action import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading stop_trading_action: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')

if check_tentacle_version('1.2.0', 'send_notification_action', 'OctoBot-Default-Tentacles'):
    try:
        from .send_notification_action import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading send_notification_action: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')

if check_tentacle_version('1.2.0', 'sell_all_currencies_action', 'OctoBot-Default-Tentacles'):
    try:
        from .sell_all_currencies_action import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading sell_all_currencies_action: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')

if check_tentacle_version('1.2.0', 'cancel_open_order_action', 'OctoBot-Default-Tentacles'):
    try:
        from .cancel_open_order_action import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading cancel_open_order_action: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')
