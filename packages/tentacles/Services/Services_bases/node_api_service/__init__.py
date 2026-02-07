import octobot_commons.constants as commons_constants
if not commons_constants.USE_MINIMAL_LIBS:
    from .node_api import NodeApiService
