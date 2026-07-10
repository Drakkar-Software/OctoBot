import octobot_commons.constants as commons_constants
from .errors import TunnelError, TunnelBackendUnavailableError, FunnelUnsupportedError
if not commons_constants.USE_MINIMAL_LIBS:
    from .tunnel import TunnelService
    # WebHookService is the historical name of TunnelService: kept as an alias so tentacle
    # activations and imports referencing "WebHookService" keep resolving.
    WebHookService = TunnelService
