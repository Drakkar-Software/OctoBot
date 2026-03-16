import octobot_commons.os_util as os_util
import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants


SAVE_STATE_AFTER_EVERY_ACTION = os_util.parse_boolean_environment_var("SAVE_STATE_AFTER_EVERY_ACTION", "false")

DEFAULT_EXTERNAL_TRIGGER_ONLY_NO_ORDER_TIMEFRAME = commons_enums.TimeFrames.ONE_DAY

# Caches settings
TICKER_CACHE_TTL = 5 * commons_constants.MINUTE_TO_SECONDS
