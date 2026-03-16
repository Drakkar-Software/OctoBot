import contextlib
import typing
import octobot_commons.profiles as commons_profiles

import octobot_flow.errors


class ProfileDataProvider:
    def __init__(self):
        self.profile_data: typing.Optional[commons_profiles.ProfileData] = None

    @contextlib.contextmanager
    def profile_data_context(self, profile_data: commons_profiles.ProfileData):
        try:
            self.profile_data = profile_data
            yield
        finally:
            self.profile_data = None

    def get_profile_data(self) -> commons_profiles.ProfileData:
        if self.profile_data is None:
            raise octobot_flow.errors.NoProfileDataError(
                f"{self.__class__.__name__} is not in a profile data context"
            )
        return self.profile_data
