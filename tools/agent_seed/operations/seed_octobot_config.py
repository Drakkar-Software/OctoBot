#  Demo agent-seed OctoBot user config.json (readonly overlays to master user).

import json
import pathlib

import octobot_commons.constants as commons_constants

import tools.agent_seed.paths as agent_seed_paths


class AgentSeedMasterReferenceTentaclesMissingError(RuntimeError):
    """Raised when master user reference_tentacles_config/tentacles_config.json is absent."""


def write_demo_user_config(
    user_folder: pathlib.Path,
    repo_root: pathlib.Path,
) -> None:
    master_root = agent_seed_paths.resolve_master_user_root_from_env(repo_root)
    reference_tentacles_file = agent_seed_paths.master_reference_tentacles_config_file(
        master_root,
    )
    if not reference_tentacles_file.is_file():
        raise AgentSeedMasterReferenceTentaclesMissingError(
            "Master reference tentacles config is missing "
            f"({reference_tentacles_file}). "
            "Install tentacles on the default user folder first "
            "(e.g. start OctoBot once on user/ or run ci-tentacles / "
            "start.py tentacles --install --all)."
        )
    config_data = {
        commons_constants.CONFIG_ACCEPTED_TERMS: True,
        commons_constants.CONFIG_PROFILE: commons_constants.DEFAULT_PROFILE,
        commons_constants.CONFIG_READONLY_REFERENCE_TENTACLES_PATH: str(
            agent_seed_paths.master_reference_tentacles_config_dir(master_root).resolve(),
        ),
        commons_constants.CONFIG_READONLY_PROFILES_PATH: str(
            agent_seed_paths.master_profiles_dir(master_root).resolve(),
        ),
    }
    config_path = agent_seed_paths.user_config_file(user_folder)
    user_folder.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(config_data, indent=2) + "\n",
        encoding="utf-8",
    )
