#  This file is part of OctoBot Node (https://github.com/Drakkar-Software/OctoBot-Node)
#  Copyright (c) 2025 Drakkar-Software, All rights reserved.
#
#  OctoBot is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  OctoBot is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  General Public License for more details.
#
#  You should have received a copy of the GNU General Public
#  License along with OctoBot. If not, see <https://www.gnu.org/licenses/>.

import asyncio
import hashlib
import json
import logging
import os
import pathlib
import re
import shutil
import typing
import uuid
from urllib import parse as urllib_parse

import aiohttp
import aiohttp.client_exceptions as aiohttp_client_exceptions

try:
    import tentacles.Services.Interfaces.node_api_interface.mobile_ui.constants as constants
    import tentacles.Services.Interfaces.node_api_interface.mobile_ui.enums as enums
    import tentacles.Services.Interfaces.node_api_interface.mobile_ui.errors as errors
    import tentacles.Services.Interfaces.node_api_interface.mobile_ui.manifest as manifest_module
except ImportError:
    import mobile_ui.constants as constants  # type: ignore[no-redef]
    import mobile_ui.enums as enums  # type: ignore[no-redef]
    import mobile_ui.errors as errors  # type: ignore[no-redef]
    import mobile_ui.manifest as manifest_module  # type: ignore[no-redef]


class MobileUiStatus(typing.TypedDict):
    state: enums.MobileUiState
    installed_version: str | None
    latest_version: str | None
    update_available: bool
    last_error: enums.MobileUiErrorCode | None


_VERSION_RE = re.compile(constants.VERSION_PATTERN)
_logger = logging.getLogger("MobileUiStore")


def _default_root_dir() -> pathlib.Path:
    return pathlib.Path(constants.DEFAULT_ROOT_DIR_RELATIVE)


def build_default_store() -> "MobileUiStore":
    update_base_url = os.environ.get(
        constants.ENV_UPDATE_BASE_URL,
        constants.DEFAULT_UPDATE_BASE_URL,
    )
    public_key = os.environ.get(
        constants.ENV_MANIFEST_PUBLIC_KEY,
        constants.DEFAULT_MANIFEST_PUBLIC_KEY,
    )
    return MobileUiStore(
        root_dir=_default_root_dir(),
        update_base_url=update_base_url,
        public_key=public_key,
    )


class MobileUiStore:
    def __init__(
        self,
        root_dir: pathlib.Path | str,
        update_base_url: str,
        public_key: str,
    ) -> None:
        self.root_dir = pathlib.Path(root_dir)
        self.update_base_url = update_base_url.rstrip("/")
        self.public_key = public_key
        self.public_keys = manifest_module.parse_public_keys(public_key)
        self.latest_version: str | None = None
        self.latest_sequence: int | None = None
        self.last_error: enums.MobileUiErrorCode | None = None
        self._install_task: asyncio.Task[None] | None = None

    def _is_configured(self) -> bool:
        return bool(self.update_base_url and self.public_keys)

    def _current_file_path(self) -> pathlib.Path:
        return self.root_dir / constants.CURRENT_FILE_NAME

    def _versions_dir(self) -> pathlib.Path:
        return self.root_dir / constants.VERSION_DIR_NAME

    def _read_installed_version(self) -> str | None:
        current_path = self._current_file_path()
        if not current_path.is_file():
            return None
        try:
            raw = json.loads(current_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        version = raw.get("version")
        if not isinstance(version, str):
            return None
        if not _VERSION_RE.fullmatch(version):
            return None
        return version

    def _version_dir(self, version: str) -> pathlib.Path:
        return self._versions_dir() / version

    def _version_dir_is_valid(self, version_dir: pathlib.Path) -> bool:
        if not version_dir.is_dir():
            return False
        index_path = version_dir / "index.html"
        manifest_path = version_dir / constants.INSTALLED_MANIFEST_FILE_NAME
        return index_path.is_file() and manifest_path.is_file()

    def active_directory(self) -> pathlib.Path | None:
        version = self._read_installed_version()
        if version is None:
            return None
        version_dir = self._version_dir(version)
        if not self._version_dir_is_valid(version_dir):
            return None
        return version_dir

    def _installed_manifest(self) -> manifest_module.Manifest | None:
        active_dir = self.active_directory()
        if active_dir is None:
            return None
        manifest_path = active_dir / constants.INSTALLED_MANIFEST_FILE_NAME
        try:
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        try:
            return manifest_module.parse_and_validate(raw)
        except errors.MobileUiError:
            return None

    def get_status(self) -> MobileUiStatus:
        if not self._is_configured():
            return self._status_payload(enums.MobileUiState.NOT_CONFIGURED)

        if self._install_task is not None and not self._install_task.done():
            return self._status_payload(enums.MobileUiState.INSTALLING)

        active_dir = self.active_directory()
        installed_version = self._read_installed_version()
        if active_dir is not None:
            state = enums.MobileUiState.READY
        elif self.last_error is not None:
            state = enums.MobileUiState.ERROR
        else:
            state = enums.MobileUiState.NOT_INSTALLED

        return self._status_payload(state, installed_version=installed_version)

    def _status_payload(
        self,
        state: enums.MobileUiState,
        installed_version: str | None = None,
    ) -> MobileUiStatus:
        if state in (enums.MobileUiState.NOT_CONFIGURED, enums.MobileUiState.INSTALLING):
            active_installed = None
        else:
            active_dir = self.active_directory()
            if active_dir is not None:
                active_installed = self._read_installed_version()
            else:
                active_installed = None
        if installed_version is None:
            installed_version = active_installed

        update_available = bool(
            self.latest_version is not None
            and installed_version is not None
            and self.latest_version != installed_version
        )

        return {
            "state": state,
            "installed_version": installed_version,
            "latest_version": self.latest_version,
            "update_available": update_available,
            "last_error": self.last_error,
        }

    def start_install(self) -> MobileUiStatus:
        if not self._is_configured():
            return self.get_status()

        if self._install_task is not None and not self._install_task.done():
            return self.get_status()
        self._install_task = asyncio.create_task(self._run_install())
        return self.get_status()

    async def _run_install(self) -> None:
        try:
            await self.install()
        except errors.MobileUiError as err:
            self.last_error = err.code
            if isinstance(err, errors.ManifestFetchError) and self.active_directory() is not None:
                _logger.warning(
                    "Mobile UI update check failed; keeping installed copy: %s",
                    err.message,
                )
            elif isinstance(err, errors.ManifestRollbackError):
                _logger.warning("Mobile UI install refused rollback: %s", err.message)
            elif not isinstance(err, errors.MobileUiNotConfiguredError):
                _logger.info("Mobile UI install failed: %s", err.message)
        except Exception as err:
            self.last_error = enums.MobileUiErrorCode.INSTALL_FAILED
            _logger.exception("Unexpected mobile UI install error: %s", err)
        finally:
            self._install_task = None

    def _assert_not_rollback(self, parsed: manifest_module.Manifest) -> None:
        installed = self._installed_manifest()
        if installed is None:
            return
        if parsed["sequence"] < installed["sequence"] or (
            parsed["sequence"] == installed["sequence"]
            and parsed["version"] != installed["version"]
        ):
            self.last_error = enums.MobileUiErrorCode.ROLLBACK_REJECTED
            raise errors.ManifestRollbackError(
                "mobile UI manifest is older than the installed version"
            )

    async def _fetch_verified_manifest(self) -> manifest_module.Manifest:
        timeout = aiohttp.ClientTimeout(
            total=constants.MANIFEST_FETCH_TIMEOUT_SECONDS,
            connect=constants.CONNECT_TIMEOUT_SECONDS,
        )
        manifest_url = f"{self.update_base_url}/{constants.MANIFEST_FILE_NAME}"
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(manifest_url) as response:
                    response.raise_for_status()
                    raw = await response.json()
        except (
            aiohttp_client_exceptions.ClientError,
            asyncio.TimeoutError,
            json.JSONDecodeError,
        ) as exc:
            raise errors.ManifestFetchError("failed to fetch mobile UI manifest") from exc

        try:
            parsed = manifest_module.parse_and_validate(raw)
        except errors.ManifestInvalidError as exc:
            self.last_error = exc.code
            raise
        try:
            manifest_module.verify_signature_any(parsed, self.public_keys)
        except errors.SignatureError as exc:
            self.last_error = exc.code
            raise

        self._assert_not_rollback(parsed)
        return parsed

    async def check_for_update(self) -> MobileUiStatus:
        if not self._is_configured():
            return self.get_status()

        if self._install_task is not None and not self._install_task.done():
            return self.get_status()

        try:
            parsed = await self._fetch_verified_manifest()
        except errors.ManifestRollbackError as err:
            self.last_error = err.code
            _logger.warning("Mobile UI update check refused rollback: %s", err.message)
            return self.get_status()
        except errors.ManifestFetchError as err:
            self.last_error = err.code
            _logger.warning("Mobile UI update check failed: %s", err.message)
            return self.get_status()
        except errors.MobileUiError as err:
            self.last_error = err.code
            _logger.info("Mobile UI update check failed: %s", err.message)
            return self.get_status()
        except Exception as err:
            self.last_error = enums.MobileUiErrorCode.INSTALL_FAILED
            _logger.exception("Unexpected mobile UI update check error: %s", err)
            return self.get_status()

        self.latest_version = parsed["version"]
        self.latest_sequence = parsed["sequence"]
        self.last_error = None
        return self.get_status()

    async def install(self) -> None:
        if not self._is_configured():
            raise errors.MobileUiNotConfiguredError("mobile UI update source is not configured")

        self.root_dir.mkdir(parents=True, exist_ok=True)
        self._versions_dir().mkdir(parents=True, exist_ok=True)

        parsed = await self._fetch_verified_manifest()

        self.latest_version = parsed["version"]
        self.latest_sequence = parsed["sequence"]
        installed_version = self._read_installed_version()
        previous_version: str | None = None
        if self.active_directory() is not None and installed_version is not None:
            previous_version = installed_version
        if (
            installed_version == parsed["version"]
            and self.active_directory() is not None
        ):
            _logger.info(
                "Mobile UI already at version %s; skipping download",
                parsed["version"],
            )
            self.last_error = None
            return

        installed_manifest = self._installed_manifest()
        tmp_dir = self.root_dir / f"{constants.TMP_DIR_PREFIX}{uuid.uuid4().hex}"
        tmp_dir.mkdir(parents=True, exist_ok=False)
        try:
            await self._download_version(parsed, installed_manifest, tmp_dir)
            manifest_path = tmp_dir / constants.INSTALLED_MANIFEST_FILE_NAME
            manifest_path.write_text(
                json.dumps(parsed, sort_keys=True, separators=(",", ":")),
                encoding="utf-8",
            )
            if not self._version_dir_is_valid(tmp_dir):
                raise errors.MobileUiInstallError("downloaded bundle failed validation")

            version_dir = self._version_dir(parsed["version"])
            if version_dir.exists():
                shutil.rmtree(version_dir)
            os.replace(tmp_dir, version_dir)

            self._write_current_json({"version": parsed["version"]})
            self.last_error = None
            _logger.info("Mobile UI installed version %s", parsed["version"])
            self._prune_old_versions(parsed["version"], previous_version)
        except errors.MobileUiError as exc:
            self.last_error = exc.code
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir, ignore_errors=True)
            raise
        except Exception as exc:
            self.last_error = enums.MobileUiErrorCode.INSTALL_FAILED
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir, ignore_errors=True)
            raise errors.MobileUiInstallError("mobile UI install failed") from exc

    def _write_current_json(self, payload: dict) -> None:
        current_path = self._current_file_path()
        temp_path = current_path.with_name(
            f".{constants.CURRENT_FILE_NAME}.{uuid.uuid4().hex}.tmp"
        )
        temp_path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
        os.replace(temp_path, current_path)

    async def _download_version(
        self,
        parsed: manifest_module.Manifest,
        installed_manifest: manifest_module.Manifest | None,
        tmp_dir: pathlib.Path,
    ) -> None:
        reuse_sha_by_path: dict[str, str] = {}
        if installed_manifest is not None:
            for file_entry in installed_manifest["files"]:
                reuse_sha_by_path[file_entry["path"]] = file_entry["sha256"]

        file_timeout = aiohttp.ClientTimeout(
            total=constants.FILE_DOWNLOAD_TIMEOUT_SECONDS,
            connect=constants.CONNECT_TIMEOUT_SECONDS,
        )
        async with aiohttp.ClientSession(timeout=file_timeout) as session:
            for file_entry in parsed["files"]:
                await self._fetch_file(
                    session,
                    parsed["version"],
                    file_entry,
                    tmp_dir,
                    reuse_sha_by_path,
                )

    async def _fetch_file(
        self,
        session: aiohttp.ClientSession,
        version: str,
        file_entry: manifest_module.ManifestFile,
        tmp_dir: pathlib.Path,
        reuse_sha_by_path: dict[str, str],
    ) -> None:
        relative_path = file_entry["path"]
        manifest_module.validate_relative_path(relative_path)
        destination = (tmp_dir / relative_path).resolve()
        if not destination.is_relative_to(tmp_dir.resolve()):
            raise errors.MobileUiInstallError("refusing to write outside temporary directory")
        destination.parent.mkdir(parents=True, exist_ok=True)

        expected_sha = file_entry["sha256"]
        expected_size = file_entry["size"]
        installed_dir = self.active_directory()
        if (
            installed_dir is not None
            and reuse_sha_by_path.get(relative_path) == expected_sha
        ):
            source = installed_dir / relative_path
            if source.is_file():
                shutil.copy2(source, destination)
                digest = hashlib.sha256()
                size = 0
                with destination.open("rb") as copied:
                    while True:
                        chunk = copied.read(65536)
                        if not chunk:
                            break
                        size += len(chunk)
                        digest.update(chunk)
                if size != expected_size or digest.hexdigest() != expected_sha:
                    raise errors.FileIntegrityError("reused file failed integrity check")
                return

        quoted_path = "/".join(
            urllib_parse.quote(segment, safe="") for segment in relative_path.split("/")
        )
        file_url = f"{self.update_base_url}/{version}/{quoted_path}"
        try:
            async with session.get(file_url) as response:
                response.raise_for_status()
                content_type = response.headers.get("Content-Type", "")
                if (
                    content_type.lower().startswith("text/html")
                    and not relative_path.endswith(".html")
                ):
                    raise errors.FileDownloadError(
                        "unexpected HTML response for non-html asset"
                    )
                digest = hashlib.sha256()
                size = 0
                with destination.open("wb") as output:
                    async for chunk in response.content.iter_chunked(65536):
                        if not chunk:
                            continue
                        size += len(chunk)
                        digest.update(chunk)
                        output.write(chunk)
        except errors.FileDownloadError:
            raise
        except aiohttp_client_exceptions.ClientError as exc:
            raise errors.FileDownloadError("failed to download mobile UI file") from exc

        if size != expected_size or digest.hexdigest() != expected_sha:
            raise errors.FileIntegrityError("downloaded file failed integrity check")

    def _prune_old_versions(
        self,
        active_version: str,
        previous_version: str | None,
    ) -> None:
        versions_dir = self._versions_dir()
        if not versions_dir.is_dir():
            return
        keep = {active_version}
        if (
            previous_version is not None
            and previous_version != active_version
            and self._version_dir_is_valid(self._version_dir(previous_version))
        ):
            keep.add(previous_version)

        for child in versions_dir.iterdir():
            if not child.is_dir():
                continue
            if child.name in keep:
                continue
            try:
                shutil.rmtree(child)
            except OSError as exc:
                _logger.debug("Failed to remove old mobile UI version %s: %s", child, exc)

        for child in self.root_dir.iterdir():
            if child.is_dir() and child.name.startswith(constants.TMP_DIR_PREFIX):
                try:
                    shutil.rmtree(child)
                except OSError as exc:
                    _logger.debug("Failed to remove stale tmp dir %s: %s", child, exc)
