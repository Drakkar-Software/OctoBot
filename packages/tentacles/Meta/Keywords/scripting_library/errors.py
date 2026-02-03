class ScriptedLibraryError(Exception):
    pass


class InvalidBacktestingDataError(ScriptedLibraryError):
    pass


class MissingReadOnlyExchangeCredentialsError(ScriptedLibraryError):
    pass


class InvalidProfileError(ScriptedLibraryError):
    pass


class InvalidTentacleProfileError(InvalidProfileError):
    pass
