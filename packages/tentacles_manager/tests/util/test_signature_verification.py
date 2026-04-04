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
from unittest import mock

import pytest

import octobot_commons.cryptography.signing as crypto_signing
import octobot_tentacles_manager.constants as constants
import octobot_tentacles_manager.util.signature_verification as sig_verif

TEST_PACKAGE_URL = "https://example.com/tentacles/packages/full/base/1.0.0/any_platform.zip"

pytestmark = pytest.mark.signature_verification


def _make_mock_session(status, body=None, raise_on_get=None):
    if raise_on_get is not None:
        mock_session = mock.MagicMock()
        mock_session.get = mock.MagicMock(side_effect=raise_on_get)
        return mock_session

    mock_resp = mock.AsyncMock()
    mock_resp.status = status
    if body is not None:
        mock_resp.read = mock.AsyncMock(return_value=body)

    mock_session = mock.MagicMock()
    mock_session.get = mock.MagicMock(return_value=mock.AsyncMock(
        __aenter__=mock.AsyncMock(return_value=mock_resp),
        __aexit__=mock.AsyncMock(return_value=False),
    ))
    return mock_session


@pytest.fixture
def key_pair():
    return crypto_signing.generate_ecdsa_key_pair()


def test_verify_package_signature_valid(key_pair):
    private_key, public_key = key_pair
    data = b"test package data"
    signature = crypto_signing.sign_data(data, private_key)
    with mock.patch.object(constants, "DRAKKAR_OFFICIAL_PUBLIC_KEY_PEM", public_key):
        assert sig_verif.verify_package_signature(data, signature) is True


def test_verify_package_signature_tampered_data(key_pair):
    private_key, public_key = key_pair
    data = b"original package data"
    signature = crypto_signing.sign_data(data, private_key)
    with mock.patch.object(constants, "DRAKKAR_OFFICIAL_PUBLIC_KEY_PEM", public_key):
        assert sig_verif.verify_package_signature(b"tampered data", signature) is False


def test_verify_package_signature_wrong_key(key_pair):
    private_key, _ = key_pair
    data = b"test package data"
    signature = crypto_signing.sign_data(data, private_key)
    _, other_public_key = crypto_signing.generate_ecdsa_key_pair()
    with mock.patch.object(constants, "DRAKKAR_OFFICIAL_PUBLIC_KEY_PEM", other_public_key):
        assert sig_verif.verify_package_signature(data, signature) is False


def test_verify_package_signature_garbage_bytes(key_pair):
    _, public_key = key_pair
    with mock.patch.object(constants, "DRAKKAR_OFFICIAL_PUBLIC_KEY_PEM", public_key):
        assert sig_verif.verify_package_signature(b"data", b"garbage-not-a-signature") is False


def test_verify_package_signature_empty_data(key_pair):
    private_key, public_key = key_pair
    signature = crypto_signing.sign_data(b"", private_key)
    with mock.patch.object(constants, "DRAKKAR_OFFICIAL_PUBLIC_KEY_PEM", public_key):
        assert sig_verif.verify_package_signature(b"", signature) is True


@pytest.mark.asyncio
async def test_sign_and_verify_roundtrip(tmp_path):
    private_key_pem, public_key_pem = crypto_signing.generate_ecdsa_key_pair()
    private_key_b64 = base64.b64encode(private_key_pem).decode()
    package_data = b"fake zip content for signing test"

    zip_path = str(tmp_path / "test.zip")
    with open(zip_path, "wb") as f:
        f.write(package_data)

    sig_path = await sig_verif.sign_package_file(zip_path, private_key_b64)
    assert sig_path == zip_path + constants.SIGNATURE_FILE_EXTENSION

    with open(sig_path, "rb") as f:
        signature = base64.b64decode(f.read())
    assert crypto_signing.verify_signature(package_data, public_key_pem, signature) is True


@pytest.mark.asyncio
async def test_sign_package_file_whitespace_in_key(tmp_path):
    private_key_pem, public_key_pem = crypto_signing.generate_ecdsa_key_pair()
    clean_b64 = base64.b64encode(private_key_pem).decode()
    # Simulate GitHub secrets with newlines and trailing whitespace
    dirty_b64 = "\n".join(clean_b64[i:i+76] for i in range(0, len(clean_b64), 76)) + "\n"
    package_data = b"fake zip content"

    zip_path = str(tmp_path / "test.zip")
    with open(zip_path, "wb") as f:
        f.write(package_data)

    sig_path = await sig_verif.sign_package_file(zip_path, dirty_b64)
    with open(sig_path, "rb") as f:
        signature = base64.b64decode(f.read())
    assert crypto_signing.verify_signature(package_data, public_key_pem, signature) is True


@pytest.mark.asyncio
async def test_sign_empty_file(tmp_path):
    private_key_pem, _ = crypto_signing.generate_ecdsa_key_pair()
    private_key_b64 = base64.b64encode(private_key_pem).decode()

    zip_path = str(tmp_path / "empty.zip")
    with open(zip_path, "wb") as f:
        f.write(b"")

    sig_path = await sig_verif.sign_package_file(zip_path, private_key_b64)
    assert (tmp_path / "empty.zip.signature").is_file()


@pytest.mark.asyncio
async def test_download_signature_successful():
    signature_bytes = b"fake-signature-bytes"
    session = _make_mock_session(200, body=base64.b64encode(signature_bytes))
    result = await sig_verif._download_signature("https://example.com/pkg.zip.signature", session)
    assert result == signature_bytes


@pytest.mark.asyncio
async def test_download_signature_404_returns_none():
    session = _make_mock_session(404)
    result = await sig_verif._download_signature("https://example.com/pkg.zip.signature", session)
    assert result is None


@pytest.mark.asyncio
async def test_download_signature_500_returns_none():
    session = _make_mock_session(500)
    result = await sig_verif._download_signature("https://example.com/pkg.zip.signature", session)
    assert result is None


@pytest.mark.asyncio
async def test_download_signature_network_error_returns_none():
    session = _make_mock_session(200, raise_on_get=ConnectionError("network down"))
    result = await sig_verif._download_signature("https://example.com/pkg.zip.signature", session)
    assert result is None


@pytest.mark.asyncio
async def test_download_signature_corrupt_base64_raises():
    session = _make_mock_session(200, body=b"this is not valid base64!!!")
    with pytest.raises(sig_verif.SignatureVerificationError, match="corrupt"):
        await sig_verif._download_signature("https://example.com/pkg.zip.signature", session)


@pytest.mark.asyncio
async def test_download_signature_oversized_response_raises():
    huge_body = b"A" * (constants.MAX_SIGNATURE_FILE_SIZE + 1)
    session = _make_mock_session(200, body=huge_body)
    with pytest.raises(sig_verif.SignatureVerificationError, match="too large"):
        await sig_verif._download_signature("https://example.com/pkg.zip.signature", session)


@pytest.mark.asyncio
async def test_verify_package_disabled_skips_check():
    mock_session = mock.MagicMock()
    with mock.patch.object(constants, "ALLOW_UNSIGNED_TENTACLES", True):
        result = await sig_verif.verify_package(
            "/tmp/fake.zip", TEST_PACKAGE_URL, mock_session
        )
    mock_session.get.assert_not_called()
    assert result is None


@pytest.mark.asyncio
async def test_verify_package_valid_signature_returns_bytes(key_pair, tmp_path):
    private_key, public_key = key_pair
    package_data = b"valid package content"
    signature = crypto_signing.sign_data(package_data, private_key)
    session = _make_mock_session(200, body=base64.b64encode(signature))

    pkg_file = tmp_path / "pkg.zip"
    pkg_file.write_bytes(package_data)

    with mock.patch.object(constants, "DRAKKAR_OFFICIAL_PUBLIC_KEY_PEM", public_key):
        result = await sig_verif.verify_package(
            str(pkg_file), TEST_PACKAGE_URL, session,
        )
        assert result == package_data


@pytest.mark.asyncio
async def test_verify_package_valid_signature_calls_correct_url(key_pair, tmp_path):
    private_key, public_key = key_pair
    package_data = b"test"
    signature = crypto_signing.sign_data(package_data, private_key)
    session = _make_mock_session(200, body=base64.b64encode(signature))

    pkg_file = tmp_path / "pkg.zip"
    pkg_file.write_bytes(package_data)

    with mock.patch.object(constants, "DRAKKAR_OFFICIAL_PUBLIC_KEY_PEM", public_key):
        await sig_verif.verify_package(str(pkg_file), TEST_PACKAGE_URL, session)
    session.get.assert_called_once_with(TEST_PACKAGE_URL + constants.SIGNATURE_FILE_EXTENSION)


@pytest.mark.asyncio
async def test_verify_package_invalid_signature_raises(key_pair, tmp_path):
    _, public_key = key_pair
    package_data = b"valid package content"
    wrong_private_key, _ = crypto_signing.generate_ecdsa_key_pair()
    bad_signature = crypto_signing.sign_data(package_data, wrong_private_key)
    session = _make_mock_session(200, body=base64.b64encode(bad_signature))

    pkg_file = tmp_path / "pkg.zip"
    pkg_file.write_bytes(package_data)

    with mock.patch.object(constants, "DRAKKAR_OFFICIAL_PUBLIC_KEY_PEM", public_key):
        with pytest.raises(sig_verif.SignatureVerificationError, match="INVALID signature"):
            await sig_verif.verify_package(
                str(pkg_file), TEST_PACKAGE_URL, session,
            )


@pytest.mark.asyncio
async def test_verify_package_missing_signature_raises(tmp_path):
    session = _make_mock_session(404)
    pkg_file = tmp_path / "pkg.zip"
    pkg_file.write_bytes(b"some data")

    with pytest.raises(sig_verif.SignatureVerificationError, match="no signature file"):
        await sig_verif.verify_package(
            str(pkg_file), TEST_PACKAGE_URL, session,
        )


@pytest.mark.asyncio
async def test_verify_package_missing_signature_allowed_when_unsigned_enabled():
    session = _make_mock_session(404)
    with mock.patch.object(constants, "ALLOW_UNSIGNED_TENTACLES", True):
        result = await sig_verif.verify_package(
            "/tmp/fake.zip", TEST_PACKAGE_URL, session,
        )
        assert result is None
    session.get.assert_not_called()


@pytest.mark.asyncio
async def test_verify_package_corrupt_signature_raises(tmp_path):
    session = _make_mock_session(200, body=b"not-valid-base64!!!")
    pkg_file = tmp_path / "pkg.zip"
    pkg_file.write_bytes(b"some data")

    with pytest.raises(sig_verif.SignatureVerificationError, match="corrupt"):
        await sig_verif.verify_package(
            str(pkg_file), TEST_PACKAGE_URL, session,
        )


def test_is_local_path_https_url():
    assert sig_verif._is_local_path("https://example.com/pkg.zip") is False


def test_is_local_path_http_url():
    assert sig_verif._is_local_path("http://example.com/pkg.zip") is False


def test_is_local_path_ftp_url():
    assert sig_verif._is_local_path("ftp://example.com/pkg.zip") is False


def test_is_local_path_sftp_url():
    assert sig_verif._is_local_path("sftp://example.com/pkg.zip") is False


def test_is_local_path_absolute():
    assert sig_verif._is_local_path("/home/user/pkg.zip") is True


def test_is_local_path_relative():
    assert sig_verif._is_local_path("./packages/pkg.zip") is True


@pytest.mark.asyncio
async def test_read_local_signature_happy_path(tmp_path):
    raw_sig = b"fake-signature-bytes"
    sig_file = tmp_path / ("pkg.zip" + constants.SIGNATURE_FILE_EXTENSION)
    sig_file.write_bytes(base64.b64encode(raw_sig))
    result = await sig_verif._read_local_signature(str(tmp_path / "pkg.zip"))
    assert result == raw_sig


@pytest.mark.asyncio
async def test_read_local_signature_missing_file(tmp_path):
    result = await sig_verif._read_local_signature(str(tmp_path / "pkg.zip"))
    assert result is None


@pytest.mark.asyncio
async def test_read_local_signature_oversized_file(tmp_path):
    sig_file = tmp_path / ("pkg.zip" + constants.SIGNATURE_FILE_EXTENSION)
    sig_file.write_bytes(b"A" * (constants.MAX_SIGNATURE_FILE_SIZE + 1))
    with pytest.raises(sig_verif.SignatureVerificationError, match="too large"):
        await sig_verif._read_local_signature(str(tmp_path / "pkg.zip"))


@pytest.mark.asyncio
async def test_read_local_signature_corrupt_base64(tmp_path):
    sig_file = tmp_path / ("pkg.zip" + constants.SIGNATURE_FILE_EXTENSION)
    sig_file.write_bytes(b"not-valid-base64!!!")
    with pytest.raises(sig_verif.SignatureVerificationError, match="corrupt"):
        await sig_verif._read_local_signature(str(tmp_path / "pkg.zip"))


@pytest.mark.asyncio
async def test_verify_package_local_valid_signature(key_pair, tmp_path):
    private_key, public_key = key_pair
    package_data = b"local package content"
    signature = crypto_signing.sign_data(package_data, private_key)

    pkg_file = tmp_path / "pkg.zip"
    pkg_file.write_bytes(package_data)
    sig_file = tmp_path / ("pkg.zip" + constants.SIGNATURE_FILE_EXTENSION)
    sig_file.write_bytes(base64.b64encode(signature))

    mock_session = mock.MagicMock()
    with mock.patch.object(constants, "DRAKKAR_OFFICIAL_PUBLIC_KEY_PEM", public_key):
        result = await sig_verif.verify_package(
            str(pkg_file), str(pkg_file), mock_session,
        )
    assert result == package_data
    mock_session.get.assert_not_called()


@pytest.mark.asyncio
async def test_verify_package_local_missing_signature(tmp_path):
    pkg_file = tmp_path / "pkg.zip"
    pkg_file.write_bytes(b"some data")

    mock_session = mock.MagicMock()
    with pytest.raises(sig_verif.SignatureVerificationError, match="no signature file"):
        await sig_verif.verify_package(
            str(pkg_file), str(pkg_file), mock_session,
        )


@pytest.mark.asyncio
async def test_verify_package_local_invalid_signature(key_pair, tmp_path):
    _, public_key = key_pair
    package_data = b"local package content"
    wrong_private_key, _ = crypto_signing.generate_ecdsa_key_pair()
    bad_signature = crypto_signing.sign_data(package_data, wrong_private_key)

    pkg_file = tmp_path / "pkg.zip"
    pkg_file.write_bytes(package_data)
    sig_file = tmp_path / ("pkg.zip" + constants.SIGNATURE_FILE_EXTENSION)
    sig_file.write_bytes(base64.b64encode(bad_signature))

    mock_session = mock.MagicMock()
    with mock.patch.object(constants, "DRAKKAR_OFFICIAL_PUBLIC_KEY_PEM", public_key):
        with pytest.raises(sig_verif.SignatureVerificationError, match="INVALID signature"):
            await sig_verif.verify_package(
                str(pkg_file), str(pkg_file), mock_session,
            )
