from octobot_tentacles_manager.api.inspector import check_tentacle_version
from octobot_commons.logging.logging_util import get_logger

if check_tentacle_version('1.2.0', 'price_threshold_event', 'OctoBot-Default-Tentacles'):
    try:
        from .price_threshold_event import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading price_threshold_event: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')

if check_tentacle_version('1.2.0', 'period_check_event', 'OctoBot-Default-Tentacles'):
    try:
        from .period_check_event import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading period_check_event: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')

if check_tentacle_version('1.2.0', 'profitability_threshold_event', 'OctoBot-Default-Tentacles'):
    try:
        from .profitability_threshold_event import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading profitability_threshold_event: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')
