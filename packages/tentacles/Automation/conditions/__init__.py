from octobot_tentacles_manager.api.inspector import check_tentacle_version
from octobot_commons.logging.logging_util import get_logger

if check_tentacle_version('1.2.0', 'scripted_condition', 'OctoBot-Default-Tentacles'):
    try:
        from .scripted_condition import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading scripted_condition: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')

if check_tentacle_version('1.2.0', 'no_condition_condition', 'OctoBot-Default-Tentacles'):
    try:
        from .no_condition_condition import *
    except Exception as e:
        get_logger('TentacleLoader').error(f'Error when loading no_condition_condition: '
                                           f'{e.__class__.__name__}{f" ({e})" if f"{e}" else ""}. If this '
                                           f'error persists, try reinstalling your tentacles via '
                                           f'"python start.py tentacles --install --all".')
