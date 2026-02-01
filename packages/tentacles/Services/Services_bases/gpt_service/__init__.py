import octobot_commons.constants as commons_constants
if not commons_constants.USE_MINIMAL_LIBS:
    from .gpt import LLMService, LLMSignalService, GPTService