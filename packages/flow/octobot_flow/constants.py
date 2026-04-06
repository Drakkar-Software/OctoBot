import os

import octobot_commons.os_util as os_util
import octobot_commons.enums as commons_enums
import octobot_commons.constants as commons_constants

import octobot_copy.constants as copy_constants


SAVE_STATE_AFTER_EVERY_ACTION = os_util.parse_boolean_environment_var("SAVE_STATE_AFTER_EVERY_ACTION", "false")

DEFAULT_EXTERNAL_TRIGGER_ONLY_NO_ORDER_TIMEFRAME = commons_enums.TimeFrames.ONE_DAY

# Copy-trading mirrored open-order grace (aligned with octobot_copy fill timeout by default)
DEFAULT_COPY_TRADING_ORPHAN_CANCEL_GRACE_SECONDS = float(copy_constants.FILL_ORDER_TIMEOUT)
DEFAULT_COPY_TRADING_ORPHAN_GRACE_ABORT_THRESHOLD = 2
DEFAULT_COPY_TRADING_ORPHAN_GRACE_PAIR_RATIO_MAX_DELTA = (
    copy_constants.DEFAULT_MIRRORED_ORPHAN_GRACE_PAIR_RATIO_MAX_DELTA
)
COPY_TRADING_GRACE_STATE_RESULT_KEY = "copy_trading_grace_state"
OPEN_ORDERS_GRACE_PERIOD_STARTED_AT_KEY = "open_orders_grace_period_started_at"
