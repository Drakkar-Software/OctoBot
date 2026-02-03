from octobot_tentacles_manager.api.inspector import check_tentacle_version
from octobot_commons.logging.logging_util import get_logger

if check_tentacle_version('1.2.0', 'python_std_operators', 'OctoBot-Default-Tentacles'):
    try:
        from .python_std_operators import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading python_std_operators: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')

if check_tentacle_version('1.2.0', 'ta_operators', 'OctoBot-Default-Tentacles'):
    try:
        from .ta_operators import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading ta_operators: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')

if check_tentacle_version('1.2.0', 'exchange_operators', 'OctoBot-Default-Tentacles'):
    try:
        from .exchange_operators import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading exchange_operators: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')
