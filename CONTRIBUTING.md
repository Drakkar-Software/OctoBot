# Contribute to OctoBot

Feel like OctoBot is missing a feature? We welcome your pull requests! 

Are you new to OctoBot? Here is an [overview of the software architecture](https://octobot.cloud/en/guides/octobot-developers-environment/architecture) and here is the [developer guide](https://octobot.cloud/en/guides/developers).

## Development philosophy

OctoBot is multi strategy, multi exchange and multi cryptocurrency.
- Any change specific to a strategy must be done in the specific code of this strategy, usually in a [tentacle](https://github.com/Drakkar-Software/OctoBot-tentacles).
- Any change specific to an exchange must be done in the exchange's associated [tentacle](https://github.com/Drakkar-Software/OctoBot-tentacles).
- Changes specific to a cryptocurrency or trading pair will be refused unless justified in the generic code.

## Contribution guidelines

- Create your PR against the `dev` branch, not `master` on the [OctoBot](https://github.com/Drakkar-Software/OctoBot) and [Tentacles](https://github.com/Drakkar-Software/OctoBot-tentacles) repositories, create them against `master` on other repositories.
- Change must be tested via associated pytest test(s) the `tests` directory.

## OctoBot additional coding style

- Change must be PEP8 compliant (max-line-length = 120).
- Use local variable only if it improves code clarity.
- Always use generators and comprehension list instead of loops when possible.
- Use `try ... except` instead of `if` statements when `if` is 99% `True`.

## Adding dependencies

For security and maintenance reasons, additional dependencies could be added to OctoBot only in case they are necessary for the global system to operate.
If your development requires an external dependency, please either:
- Open an issue to discuss the integration of this dependency into the main code.
- Make this dependency import optional in your code at import time so that the main OctoBot can still import your code and leave the reponsability to the user to install this dependency to use your code.
