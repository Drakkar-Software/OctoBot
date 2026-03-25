#  Drakkar-Software OctoBot-Tentacles
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import asyncio
import os
import shutil
import socket
import typing

import octobot_commons.constants as commons_constants
import octobot_commons.monitored_process as monitored_process
import octobot_services.constants as services_constants
import octobot_services.services as services
import octobot_trading.api.exchange as trading_exchange_api
import octobot_trading.exchanges.config.proxy_config as proxy_config_module


class _TorProcess(monitored_process.MonitoredProcess):
    READINESS_STRING = "Bootstrapped 100%"
    READINESS_TIMEOUT_SECONDS = 120.0
    ERROR_PATTERNS = [
        "[err]",
        "[warn] Could not bind",
    ]

    def __init__(self, cmd_args: list[str]):
        super().__init__()
        self._cmd_args = cmd_args

    def _get_subprocess_args(self) -> list[str]:
        return self._cmd_args


class TorService(services.AbstractService):
    BACKTESTING_ENABLED = False

    def __init__(self):
        super().__init__()
        self.tor_binary_path: str = services_constants.DEFAULT_TOR_BINARY_PATH
        self.socks_port: int = services_constants.DEFAULT_TOR_SOCKS_PORT
        self.http_port: int = services_constants.DEFAULT_TOR_HTTP_PORT
        self.control_port: int = services_constants.DEFAULT_TOR_CONTROL_PORT
        self.auto_update_torrc: bool = False
        self.torrc_extra: str = ""
        self._tor_process: typing.Optional[_TorProcess] = None
        self._managed_process: bool = False
        self._connected: bool = False
        self._tor_data_dir: typing.Optional[str] = None

    def get_fields_description(self):
        return {
            services_constants.CONFIG_TOR_BINARY_PATH:
                "Path to the tor binary. Use 'tor' if it is in your system PATH.",
            services_constants.CONFIG_TOR_SOCKS_PORT:
                "SOCKS5 proxy port exposed by Tor (default: 9050).",
            services_constants.CONFIG_TOR_HTTP_PORT:
                "HTTP CONNECT proxy port. Set to 0 to disable the HTTP proxy "
                "(requires an external HTTP-to-SOCKS wrapper like privoxy or polipo).",
            services_constants.CONFIG_TOR_CONTROL_PORT:
                "Tor control port for sending commands (new identity, etc.). Default: 9051.",
            services_constants.CONFIG_TOR_AUTO_UPDATE_TORRC:
                "When enabled, the service writes a minimal torrc before starting Tor.",
            services_constants.CONFIG_TOR_TORRC_EXTRA:
                "Extra lines appended to the generated torrc (one directive per line).",
        }

    def get_default_value(self):
        return {
            services_constants.CONFIG_TOR_BINARY_PATH: services_constants.DEFAULT_TOR_BINARY_PATH,
            services_constants.CONFIG_TOR_SOCKS_PORT: services_constants.DEFAULT_TOR_SOCKS_PORT,
            services_constants.CONFIG_TOR_HTTP_PORT: services_constants.DEFAULT_TOR_HTTP_PORT,
            services_constants.CONFIG_TOR_CONTROL_PORT: services_constants.DEFAULT_TOR_CONTROL_PORT,
            services_constants.CONFIG_TOR_AUTO_UPDATE_TORRC: False,
            services_constants.CONFIG_TOR_TORRC_EXTRA: "",
        }

    def get_required_config(self):
        return [services_constants.CONFIG_TOR_SOCKS_PORT]

    @staticmethod
    def is_setup_correctly(config):
        return (
            services_constants.CONFIG_TOR in config.get(services_constants.CONFIG_CATEGORY_SERVICES, {})
            and services_constants.CONFIG_SERVICE_INSTANCE
            in config[services_constants.CONFIG_CATEGORY_SERVICES][services_constants.CONFIG_TOR]
        )

    @staticmethod
    def get_is_enabled(config):
        return config.get(services_constants.CONFIG_CATEGORY_SERVICES, {}).get(
            services_constants.CONFIG_TOR, {}
        ).get(services_constants.CONFIG_TOR_ENABLED, False)

    def has_required_configuration(self):
        try:
            tor_config = self.config[services_constants.CONFIG_CATEGORY_SERVICES][services_constants.CONFIG_TOR]
            return self.check_required_config(tor_config)
        except KeyError:
            return False

    def get_type(self):
        return services_constants.CONFIG_TOR

    def get_endpoint(self):
        return self

    def get_website_url(self):
        return "https://www.torproject.org"

    def get_logo(self):
        return "https://upload.wikimedia.org/wikipedia/commons/1/15/Tor-logo-2011-flat.svg"

    @classmethod
    def get_help_page(cls) -> str:
        return ""

    @staticmethod
    def get_should_warn():
        return False

    def is_running(self):
        return self._connected

    def get_socks_proxy_url(self) -> str:
        return f"socks5h://127.0.0.1:{self.socks_port}"

    def get_http_proxy_url(self) -> typing.Optional[str]:
        if self.http_port and self.http_port > 0:
            return f"http://127.0.0.1:{self.http_port}"
        return None

    def get_aiohttp_proxy(self) -> str:
        return self.get_socks_proxy_url()

    def is_connected(self) -> bool:
        return self._connected

    def create_proxy_config(self) -> proxy_config_module.ProxyConfig:
        socks_url = self.get_socks_proxy_url()
        http_url = self.get_http_proxy_url()
        return proxy_config_module.ProxyConfig(
            http_proxy=http_url,
            https_proxy=http_url,
            socks_proxy=socks_url,
            ws_socks_proxy=socks_url,
            proxy_host=f"127.0.0.1:{self.socks_port}",
        )

    async def request_new_identity(self) -> bool:
        return await asyncio.get_running_loop().run_in_executor(
            None, self._send_control_command, "SIGNAL NEWNYM"
        )

    async def prepare(self) -> None:
        tor_config = self.config.get(services_constants.CONFIG_CATEGORY_SERVICES, {}).get(
            services_constants.CONFIG_TOR, {}
        )
        self.tor_binary_path = os.getenv(
            services_constants.ENV_TOR_BINARY_PATH,
            tor_config.get(
                services_constants.CONFIG_TOR_BINARY_PATH,
                services_constants.DEFAULT_TOR_BINARY_PATH,
            ),
        )
        self.socks_port = int(
            os.getenv(
                services_constants.ENV_TOR_SOCKS_PORT,
                tor_config.get(
                    services_constants.CONFIG_TOR_SOCKS_PORT,
                    services_constants.DEFAULT_TOR_SOCKS_PORT,
                ),
            )
        )
        self.http_port = int(
            os.getenv(
                services_constants.ENV_TOR_HTTP_PORT,
                tor_config.get(
                    services_constants.CONFIG_TOR_HTTP_PORT,
                    services_constants.DEFAULT_TOR_HTTP_PORT,
                ),
            )
        )
        self.control_port = int(
            os.getenv(
                services_constants.ENV_TOR_CONTROL_PORT,
                tor_config.get(
                    services_constants.CONFIG_TOR_CONTROL_PORT,
                    services_constants.DEFAULT_TOR_CONTROL_PORT,
                ),
            )
        )
        self.auto_update_torrc = tor_config.get(
            services_constants.CONFIG_TOR_AUTO_UPDATE_TORRC, False
        )
        self.torrc_extra = tor_config.get(services_constants.CONFIG_TOR_TORRC_EXTRA, "")

        if not self._is_tor_binary_available():
            self.logger.error(
                f"Tor binary not found at '{self.tor_binary_path}'. "
                "Please install Tor on your system."
            )
            return

        if self._is_tor_already_running():
            self.logger.info(
                f"Tor SOCKS proxy already listening on port {self.socks_port}, "
                "attaching to existing Tor process."
            )
            if self._verify_tor_connection():
                self._connected = True
            else:
                self.logger.warning(
                    f"Port {self.socks_port} is open but could not verify it is Tor "
                    "(control port unreachable). Assuming Tor is running."
                )
                self._connected = True
            trading_exchange_api.set_all_exchanges_proxy_config(self.create_proxy_config())
            return

        if self.auto_update_torrc:
            self._write_torrc()

        await self._start_tor_process()

    def _build_tor_cmd(self) -> list[str]:
        cmd = [self.tor_binary_path]
        if self.auto_update_torrc:
            torrc_path = self._get_torrc_path()
            if os.path.isfile(torrc_path):
                cmd.extend(["-f", torrc_path])
                return cmd
            self.logger.warning(
                "auto-update-torrc is enabled but no torrc was generated. "
                "Using command-line arguments."
            )
        self._append_cli_args(cmd)
        return cmd

    async def _start_tor_process(self) -> None:
        cmd = self._build_tor_cmd()
        self._tor_process = _TorProcess(cmd)
        try:
            await self._tor_process.__aenter__()
            self._managed_process = True
            self._connected = True
            trading_exchange_api.set_all_exchanges_proxy_config(self.create_proxy_config())
        except monitored_process.MonitoredProcessConfigurationError as e:
            self.logger.error(f"Could not start Tor: {e}")
            self._tor_process = None
        except monitored_process.MonitoredProcessReadyTimeoutError:
            self.logger.error("Tor failed to bootstrap within the timeout period.")
            self._tor_process.log_output(20)
            await self._stop_managed_process()
        except monitored_process.MonitoredProcessOutputError as e:
            self.logger.error(f"Tor process error: {e}")
            await self._stop_managed_process()
        except monitored_process.MonitoredProcessExitedError as e:
            self.logger.error(f"Tor process exited prematurely: {e}")
            await self._stop_managed_process()

    def _append_cli_args(self, cmd: list) -> None:
        cmd.extend(["--SocksPort", str(self.socks_port)])
        cmd.extend(["--ControlPort", str(self.control_port)])
        if self.http_port and self.http_port > 0:
            cmd.extend(["--HTTPTunnelPort", str(self.http_port)])
        cmd.extend(["--DataDirectory", os.path.join(self._get_tor_data_dir(), "data")])

    def _is_tor_binary_available(self) -> bool:
        path = self.tor_binary_path.strip()
        if not path:
            return False
        if os.sep in path or path.startswith("/"):
            return os.path.isfile(path) and os.access(path, os.X_OK)
        return shutil.which(path) is not None

    @staticmethod
    def _is_port_open(port: int, host: str = "127.0.0.1") -> bool:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except OSError:
            return False

    def _is_tor_already_running(self) -> bool:
        return self._is_port_open(self.socks_port)

    def _verify_tor_connection(self) -> bool:
        try:
            with socket.create_connection(("127.0.0.1", self.control_port), timeout=3) as sock:
                sock.sendall(b'AUTHENTICATE\r\n')
                if not sock.recv(256).decode().startswith("250"):
                    return False
                sock.sendall(b"GETINFO version\r\n")
                resp = sock.recv(256).decode()
                if "250-version=" in resp:
                    self.logger.info(f"Verified Tor connection: {resp.strip()}")
                    return True
                return False
        except OSError:
            return False

    def _get_tor_data_dir(self) -> str:
        if self._tor_data_dir is None:
            self._tor_data_dir = os.path.join(commons_constants.USER_FOLDER, "tor")
            os.makedirs(self._tor_data_dir, exist_ok=True)
        return self._tor_data_dir

    def _get_torrc_path(self) -> str:
        return os.path.join(self._get_tor_data_dir(), "generated_torrc")

    def _write_torrc(self) -> None:
        torrc_path = self._get_torrc_path()
        data_dir = self._get_tor_data_dir()
        lines = [
            f"SocksPort {self.socks_port}",
            f"ControlPort {self.control_port}",
            f"DataDirectory {os.path.join(data_dir, 'data')}",
        ]
        if self.http_port and self.http_port > 0:
            lines.append(f"HTTPTunnelPort {self.http_port}")
        if self.torrc_extra:
            lines.append(self.torrc_extra)
        self.logger.info(f"Writing generated torrc to {torrc_path}")
        with open(torrc_path, "w") as f:
            f.write("\n".join(lines) + "\n")

    def _send_control_command(self, command: str) -> bool:
        try:
            with socket.create_connection(("127.0.0.1", self.control_port), timeout=5) as sock:
                sock.sendall(b'AUTHENTICATE\r\n')
                if not sock.recv(256).decode().startswith("250"):
                    self.logger.error("Tor control authentication failed.")
                    return False
                sock.sendall(f"{command}\r\n".encode())
                resp = sock.recv(256).decode()
                if resp.startswith("250"):
                    self.logger.debug(f"Tor control command '{command}' succeeded.")
                    return True
                self.logger.warning(f"Tor control command '{command}' returned: {resp.strip()}")
                return False
        except Exception as e:
            self.logger.error(f"Failed to send Tor control command: {e}")
            return False

    def get_successful_startup_message(self):
        proxies = [f"SOCKS5 on port {self.socks_port}"]
        if self.http_port and self.http_port > 0:
            proxies.append(f"HTTP on port {self.http_port}")
        proxy_info = ", ".join(proxies)
        return (
            f"Tor service ready ({proxy_info})",
            self._connected,
        )

    async def _stop_managed_process(self) -> None:
        if self._tor_process is not None:
            try:
                await self._tor_process.__aexit__(None, None, None)
            except Exception:
                pass
            self._tor_process = None

    async def stop(self):
        if self._managed_process:
            self.logger.info("Stopping managed Tor process.")
            await self._stop_managed_process()
        self._managed_process = False
        self._connected = False
