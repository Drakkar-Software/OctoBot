import dataclasses
import typing
import octobot_commons.dataclasses


@dataclasses.dataclass
class UserAuthentication(octobot_commons.dataclasses.FlexibleDataclass):
    email: typing.Optional[str] = None
    password: typing.Optional[str] = None
    hidden: bool = False
    user_id: typing.Optional[str] = None
    auth_key: typing.Optional[str] = None
    encrypted_keys_by_exchange: dict[str, str] = dataclasses.field(default_factory=dict)

    def has_auth_details(self) -> bool:
        return bool(self.password or self.auth_key)