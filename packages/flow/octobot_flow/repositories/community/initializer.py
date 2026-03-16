import octobot.community
import octobot_commons.configuration


def initialize_community_authentication():
    octobot.community.IdentifiersProvider.use_production()
    configuration = get_stateless_configuration()
    # create CommunityAuthentication singleton
    octobot.community.CommunityAuthentication.create(configuration)


def get_stateless_configuration() -> octobot_commons.configuration.Configuration:
    configuration = octobot_commons.configuration.Configuration(None, None)
    configuration.config = {}
    # disable save
    configuration.save = lambda *_, **__: _ # type: ignore
    return configuration
