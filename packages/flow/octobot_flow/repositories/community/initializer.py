import octobot.community


def initialize_community_authentication():
    octobot.community.IdentifiersProvider.use_production()
    configuration = octobot.community.get_stateless_configuration()
    # create CommunityAuthentication singleton
    octobot.community.CommunityAuthentication.create(configuration)
