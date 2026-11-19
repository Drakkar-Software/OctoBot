#  Agent seed demo logging_config.ini tests.

import configparser
import logging
import logging.config

import tools.agent_seed.operations.seed_logging_config as agent_seed_seed_logging_config
import tools.agent_seed.operations.seed_run as agent_seed_seed_run
import tools.agent_seed.paths as agent_seed_paths


def _handler_level(logging_config_path, handler_section: str) -> str:
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    parser.read(logging_config_path, encoding="utf-8")
    return parser[handler_section]["level"]


def _assert_file_config_loads(logging_config_path, monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "logs").mkdir(parents=True, exist_ok=True)
    logging.config.fileConfig(
        logging_config_path,
        disable_existing_loggers=False,
    )


def _install_master_reference_tentacles(monkeypatch, tmp_path):
    master_root = tmp_path / "master-user"
    reference_dir = agent_seed_paths.master_reference_tentacles_config_dir(master_root)
    reference_dir.mkdir(parents=True)
    (reference_dir / agent_seed_paths.TENTACLES_CONFIG_FILE_NAME).write_text(
        "{}",
        encoding="utf-8",
    )
    monkeypatch.setenv(
        agent_seed_paths.OCTOBOT_AGENT_SEED_MASTER_USER_ROOT_ENV,
        str(master_root),
    )
    return master_root


class TestWriteDemoLoggingConfig:
    def test_writes_debug_handler_levels_and_file_config_loads(
        self,
        tmp_path,
        monkeypatch,
    ):
        user_folder = tmp_path / "agent-seed-user"
        agent_seed_seed_logging_config.write_demo_logging_config(user_folder)
        logging_config_path = agent_seed_paths.logging_config_file(user_folder)
        assert logging_config_path.is_file()
        assert _handler_level(logging_config_path, "handler_consoleHandler") == "DEBUG"
        assert _handler_level(logging_config_path, "handler_fileHandler") == "DEBUG"
        _assert_file_config_loads(logging_config_path, monkeypatch, tmp_path)


class TestRunSeedLoggingConfig:
    def test_idempotent_run_seed_overwrites_stale_logging_config(
        self,
        tmp_path,
        monkeypatch,
    ):
        _install_master_reference_tentacles(monkeypatch, tmp_path)
        user_folder = tmp_path / "agent-seed-user"
        sqlite_path = user_folder / "tasks.db"
        agent_seed_seed_run.run_seed(
            user_folder=user_folder,
            clear=False,
            node_sqlite_file=sqlite_path,
            repo_root=tmp_path,
        )
        logging_config_path = agent_seed_paths.logging_config_file(user_folder)
        logging_config_path.write_text(
            "[handler_consoleHandler]\nlevel=INFO\n",
            encoding="utf-8",
        )
        agent_seed_seed_run.run_seed(
            user_folder=user_folder,
            clear=False,
            node_sqlite_file=sqlite_path,
            repo_root=tmp_path,
        )
        assert _handler_level(logging_config_path, "handler_consoleHandler") == "DEBUG"
        assert _handler_level(logging_config_path, "handler_fileHandler") == "DEBUG"
        _assert_file_config_loads(logging_config_path, monkeypatch, tmp_path)
