#  Drakkar-Software OctoBot-Commons
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
import pytest

from cryptography.hazmat.primitives.asymmetric import ec

import octobot_commons.cryptography as cryptography


def test_generate_ecdsa_key_pair_default_curve():
    """Test ECDSA key pair generation with default curve (SECP256R1)."""
    private_key_pem, public_key_pem = cryptography.generate_ecdsa_key_pair()

    assert isinstance(private_key_pem, bytes)
    assert isinstance(public_key_pem, bytes)
    assert b"BEGIN PRIVATE KEY" in private_key_pem
    assert b"BEGIN PUBLIC KEY" in public_key_pem
    assert b"END PRIVATE KEY" in private_key_pem
    assert b"END PUBLIC KEY" in public_key_pem


def test_generate_ecdsa_key_pair_custom_curve():
    """Test ECDSA key pair generation with custom curve."""
    private_key_pem, public_key_pem = cryptography.generate_ecdsa_key_pair(curve=ec.SECP384R1())

    assert isinstance(private_key_pem, bytes)
    assert isinstance(public_key_pem, bytes)
    assert b"BEGIN PRIVATE KEY" in private_key_pem
    assert b"BEGIN PUBLIC KEY" in public_key_pem


def test_generate_ecdsa_key_pair_different_keys():
    """Test that generating multiple key pairs produces different keys."""
    private_key_1, public_key_1 = cryptography.generate_ecdsa_key_pair()
    private_key_2, public_key_2 = cryptography.generate_ecdsa_key_pair()

    assert private_key_1 != private_key_2
    assert public_key_1 != public_key_2


def test_sign_data():
    """Test signing data with ECDSA private key."""
    private_key_pem, public_key_pem = cryptography.generate_ecdsa_key_pair()
    data = b"Hello, World! This is test data."

    signature = cryptography.sign_data(data, private_key_pem)

    assert isinstance(signature, bytes)
    assert len(signature) > 0


def test_sign_data_different_data_produces_different_signatures():
    """Test that signing different data produces different signatures."""
    private_key_pem, _ = cryptography.generate_ecdsa_key_pair()
    data1 = b"First message"
    data2 = b"Second message"

    signature1 = cryptography.sign_data(data1, private_key_pem)
    signature2 = cryptography.sign_data(data2, private_key_pem)

    assert signature1 != signature2


def test_sign_data_same_data_produces_different_signatures():
    """Test that signing the same data multiple times produces different signatures (ECDSA is non-deterministic)."""
    private_key_pem, _ = cryptography.generate_ecdsa_key_pair()
    data = b"Same message"

    signature1 = cryptography.sign_data(data, private_key_pem)
    signature2 = cryptography.sign_data(data, private_key_pem)

    # ECDSA signatures are non-deterministic, so they should be different
    assert signature1 != signature2


def test_verify_signature_valid():
    """Test verifying a valid signature."""
    private_key_pem, public_key_pem = cryptography.generate_ecdsa_key_pair()
    data = b"Test data to sign and verify"

    signature = cryptography.sign_data(data, private_key_pem)
    is_valid = cryptography.verify_signature(data, public_key_pem, signature)

    assert is_valid is True


def test_verify_signature_invalid_data():
    """Test verifying a signature with wrong data."""
    private_key_pem, public_key_pem = cryptography.generate_ecdsa_key_pair()
    original_data = b"Original data"
    wrong_data = b"Wrong data"

    signature = cryptography.sign_data(original_data, private_key_pem)
    is_valid = cryptography.verify_signature(wrong_data, public_key_pem, signature)

    assert is_valid is False


def test_verify_signature_invalid_signature():
    """Test verifying with a corrupted signature."""
    private_key_pem, public_key_pem = cryptography.generate_ecdsa_key_pair()
    data = b"Test data"

    signature = cryptography.sign_data(data, private_key_pem)
    # Corrupt the signature
    corrupted_signature = signature[:-1] + b"\x00"

    is_valid = cryptography.verify_signature(data, public_key_pem, corrupted_signature)

    assert is_valid is False


def test_verify_signature_wrong_public_key():
    """Test verifying a signature with a different public key."""
    private_key_pem_1, public_key_pem_1 = cryptography.generate_ecdsa_key_pair()
    _, public_key_pem_2 = cryptography.generate_ecdsa_key_pair()
    data = b"Test data"

    signature = cryptography.sign_data(data, private_key_pem_1)
    is_valid = cryptography.verify_signature(data, public_key_pem_2, signature)

    assert is_valid is False


def test_sign_and_verify_round_trip():
    """Test complete sign and verify round trip with various data sizes."""
    private_key_pem, public_key_pem = cryptography.generate_ecdsa_key_pair()

    test_cases = [
        b"",
        b"a",
        b"Short message",
        b"Medium length message with some content",
        b"Very long message " * 100,
    ]

    for data in test_cases:
        signature = cryptography.sign_data(data, private_key_pem)
        is_valid = cryptography.verify_signature(data, public_key_pem, signature)
        assert is_valid is True, f"Verification failed for data: {data[:50]}"


def test_sign_data_invalid_private_key():
    """Test signing with invalid private key raises ValueError."""
    invalid_key = b"-----BEGIN PRIVATE KEY-----\nInvalid\n-----END PRIVATE KEY-----"
    data = b"Test data"

    with pytest.raises(ValueError):
        cryptography.sign_data(data, invalid_key)


def test_verify_signature_invalid_public_key():
    """Test verifying with invalid public key raises ValueError."""
    _, public_key_pem = cryptography.generate_ecdsa_key_pair()
    invalid_key = b"-----BEGIN PUBLIC KEY-----\nInvalid\n-----END PUBLIC KEY-----"
    data = b"Test data"
    signature = b"fake signature"

    with pytest.raises(ValueError):
        cryptography.verify_signature(data, invalid_key, signature)


def test_sign_data_with_rsa_key_raises_error():
    """Test that signing with an RSA key (not ECDSA) raises ValueError."""
    rsa_private_key, _ = cryptography.generate_rsa_key_pair()
    data = b"Test data"

    with pytest.raises(ValueError, match="Private key must be an ECDSA key"):
        cryptography.sign_data(data, rsa_private_key)


def test_verify_signature_with_rsa_key_raises_error():
    """Test that verifying with an RSA key (not ECDSA) raises ValueError."""
    _, rsa_public_key = cryptography.generate_rsa_key_pair()
    data = b"Test data"
    signature = b"fake signature"

    with pytest.raises(ValueError, match="Public key must be an ECDSA key"):
        cryptography.verify_signature(data, rsa_public_key, signature)
