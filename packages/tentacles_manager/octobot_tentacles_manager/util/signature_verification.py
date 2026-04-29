#  Drakkar-Software OctoBot-Tentacles-Manager
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
import base64
import binascii
import os

import aiofiles

import octobot_commons.logging as commons_logging
import octobot_commons.cryptography.signing as crypto_signing
import octobot_tentacles_manager.constants as constants


class SignatureVerificationError(Exception):
    pass


def _is_local_path(path_or_url):
    return not (path_or_url.startswith("https://")
                or path_or_url.startswith("http://")
                or path_or_url.startswith("ftp://")
                or path_or_url.startswith("sftp://"))


async def _read_local_signature(file_path):
    logger = commons_logging.get_logger("SignatureVerification")
    signature_path = file_path + constants.SIGNATURE_FILE_EXTENSION
    if not os.path.isfile(signature_path):
        logger.debug(f"Signature file not found at {signature_path}")
        return None
    try:
        async with aiofiles.open(signature_path, "rb") as f:
            raw = await f.read()
        if len(raw) > constants.MAX_SIGNATURE_FILE_SIZE:
            raise SignatureVerificationError(
                f"Signature file at {signature_path} is too large "
                f"({len(raw)} bytes, max {constants.MAX_SIGNATURE_FILE_SIZE})"
            )
        return base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError) as decode_err:
        raise SignatureVerificationError(
            f"Signature file at {signature_path} is corrupt "
            f"(invalid base64): {decode_err}"
        ) from decode_err


async def _download_signature(signature_url, aiohttp_session):
    logger = commons_logging.get_logger("SignatureVerification")
    try:
        async with aiohttp_session.get(signature_url) as resp:
            if resp.status == 200:
                raw = await resp.read()
                if len(raw) > constants.MAX_SIGNATURE_FILE_SIZE:
                    raise SignatureVerificationError(
                        f"Signature file at {signature_url} is too large "
                        f"({len(raw)} bytes, max {constants.MAX_SIGNATURE_FILE_SIZE})"
                    )
                try:
                    return base64.b64decode(raw, validate=True)
                except (binascii.Error, ValueError) as decode_err:
                    raise SignatureVerificationError(
                        f"Signature file at {signature_url} is corrupt "
                        f"(invalid base64): {decode_err}"
                    ) from decode_err
            logger.debug(
                f"Signature file not found at {signature_url} (HTTP {resp.status})"
            )
            return None
    except SignatureVerificationError:
        raise
    except Exception as err:
        logger.warning(f"Failed to download signature from {signature_url}: {err}")
        return None


def verify_package_signature(package_data, signature):
    try:
        return crypto_signing.verify_signature(
            data=package_data,
            public_key_pem=constants.DRAKKAR_OFFICIAL_PUBLIC_KEY_PEM,
            signature=signature,
        )
    except ValueError:
        return False


async def verify_package(compressed_file, tentacles_path_or_url, aiohttp_session):
    logger = commons_logging.get_logger("SignatureVerification")

    if constants.ALLOW_UNSIGNED_TENTACLES:
        logger.warning(
            f"Signature verification is disabled (ALLOW_UNSIGNED_TENTACLES is set). "
            f"Skipping verification for {tentacles_path_or_url}"
        )
        return None

    if _is_local_path(tentacles_path_or_url):
        signature = await _read_local_signature(tentacles_path_or_url)
    else:
        signature_url = tentacles_path_or_url + constants.SIGNATURE_FILE_EXTENSION
        signature = await _download_signature(signature_url, aiohttp_session)

    if signature is None:
        raise SignatureVerificationError(
            f"Tentacles package at {tentacles_path_or_url} has no signature file. "
            f"Refusing to install unsigned package. "
            f"Set ALLOW_UNSIGNED_TENTACLES=true to bypass signature verification."
        )

    async with aiofiles.open(compressed_file, "rb") as f:
        package_data = await f.read()

    if verify_package_signature(package_data, signature):
        logger.info(
            f"Tentacles package signature verified successfully for {tentacles_path_or_url}"
        )
        return package_data

    raise SignatureVerificationError(
        f"Tentacles package at {tentacles_path_or_url} has an INVALID signature. "
        f"The package may have been tampered with. Refusing to install."
    )


async def sign_package_file(zip_path, private_key_pem_b64):
    private_key_pem = crypto_signing.parse_private_key_pem(private_key_pem_b64)
    async with aiofiles.open(zip_path, "rb") as f:
        data = await f.read()
    signature = crypto_signing.sign_data(data, private_key_pem)
    sig_path = zip_path + constants.SIGNATURE_FILE_EXTENSION
    async with aiofiles.open(sig_path, "wb") as f:
        await f.write(base64.b64encode(signature))
    commons_logging.get_logger("SignatureVerification").info(
        f"Signed package {zip_path} -> {sig_path}"
    )
    return sig_path
