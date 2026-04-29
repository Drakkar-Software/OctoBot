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

import octobot_commons.cryptography as cryptography


def test_generate_rsa_key_pair_default_size():
    """Test RSA key pair generation with default size (4096 bits)."""
    private_key_pem, public_key_pem = cryptography.generate_rsa_key_pair()

    assert isinstance(private_key_pem, bytes)
    assert isinstance(public_key_pem, bytes)
    assert b"BEGIN RSA PRIVATE KEY" in private_key_pem or b"BEGIN PRIVATE KEY" in private_key_pem
    assert b"BEGIN PUBLIC KEY" in public_key_pem
    assert b"END RSA PRIVATE KEY" in private_key_pem or b"END PRIVATE KEY" in private_key_pem
    assert b"END PUBLIC KEY" in public_key_pem


def test_generate_rsa_key_pair_custom_size():
    """Test RSA key pair generation with custom key size."""
    private_key_pem, public_key_pem = cryptography.generate_rsa_key_pair(key_size=2048)

    assert isinstance(private_key_pem, bytes)
    assert isinstance(public_key_pem, bytes)
    assert b"BEGIN RSA PRIVATE KEY" in private_key_pem or b"BEGIN PRIVATE KEY" in private_key_pem
    assert b"BEGIN PUBLIC KEY" in public_key_pem


def test_generate_rsa_key_pair_different_keys():
    """Test that generating multiple key pairs produces different keys."""
    private_key_1, public_key_1 = cryptography.generate_rsa_key_pair()
    private_key_2, public_key_2 = cryptography.generate_rsa_key_pair()

    assert private_key_1 != private_key_2
    assert public_key_1 != public_key_2


def test_generate_rsa_key_pair_invalid_size():
    """Test that generating RSA key with invalid size raises ValueError."""
    with pytest.raises(ValueError, match="RSA key size must be at least 2048 bits"):
        cryptography.generate_rsa_key_pair(key_size=1024)


def test_generate_aes_key_default_size():
    """Test AES key generation with default size (32 bytes)."""
    aes_key = cryptography.generate_aes_key()

    assert isinstance(aes_key, bytes)
    assert len(aes_key) == 32


def test_generate_aes_key_custom_size():
    """Test AES key generation with custom size."""
    aes_key = cryptography.generate_aes_key(key_size=16)

    assert isinstance(aes_key, bytes)
    assert len(aes_key) == 16


def test_generate_aes_key_different_keys():
    """Test that generating multiple AES keys produces different keys."""
    aes_key_1 = cryptography.generate_aes_key()
    aes_key_2 = cryptography.generate_aes_key()

    assert aes_key_1 != aes_key_2


def test_generate_aes_key_invalid_size():
    """Test that generating AES key with invalid size raises ValueError."""
    with pytest.raises(ValueError, match="Key size must be at least 1 byte"):
        cryptography.generate_aes_key(key_size=0)


def test_generate_iv_default_size():
    """Test IV generation with default size (12 bytes)."""
    iv = cryptography.generate_iv()

    assert isinstance(iv, bytes)
    assert len(iv) == 12


def test_generate_iv_custom_size():
    """Test IV generation with custom size."""
    iv = cryptography.generate_iv(iv_size=16)

    assert isinstance(iv, bytes)
    assert len(iv) == 16


def test_generate_iv_different_ivs():
    """Test that generating multiple IVs produces different values."""
    iv_1 = cryptography.generate_iv()
    iv_2 = cryptography.generate_iv()

    assert iv_1 != iv_2


def test_generate_iv_invalid_size():
    """Test that generating IV with invalid size raises ValueError."""
    with pytest.raises(ValueError, match="IV size must be at least 1 byte"):
        cryptography.generate_iv(iv_size=0)


def test_rsa_encrypt_decrypt_aes_key():
    """Test RSA encryption and decryption of AES key round trip."""
    private_key_pem, public_key_pem = cryptography.generate_rsa_key_pair()
    aes_key = cryptography.generate_aes_key()

    encrypted_key = cryptography.rsa_encrypt_aes_key(aes_key, public_key_pem)
    decrypted_key = cryptography.rsa_decrypt_aes_key(encrypted_key, private_key_pem)

    assert decrypted_key == aes_key
    assert encrypted_key != aes_key


def test_rsa_encrypt_aes_key_different_encryptions():
    """Test that encrypting the same AES key multiple times produces different ciphertexts."""
    _, public_key_pem = cryptography.generate_rsa_key_pair()
    aes_key = cryptography.generate_aes_key()

    encrypted_key_1 = cryptography.rsa_encrypt_aes_key(aes_key, public_key_pem)
    encrypted_key_2 = cryptography.rsa_encrypt_aes_key(aes_key, public_key_pem)

    # RSA OAEP uses random padding, so same plaintext produces different ciphertexts
    assert encrypted_key_1 != encrypted_key_2


def test_rsa_encrypt_aes_key_invalid_public_key():
    """Test that encrypting with invalid public key raises ValueError."""
    invalid_key = b"-----BEGIN PUBLIC KEY-----\nInvalid\n-----END PUBLIC KEY-----"
    aes_key = cryptography.generate_aes_key()

    with pytest.raises(ValueError):
        cryptography.rsa_encrypt_aes_key(aes_key, invalid_key)


def test_rsa_decrypt_aes_key_invalid_private_key():
    """Test that decrypting with invalid private key raises ValueError."""
    private_key_pem, public_key_pem = cryptography.generate_rsa_key_pair()
    aes_key = cryptography.generate_aes_key()
    encrypted_key = cryptography.rsa_encrypt_aes_key(aes_key, public_key_pem)

    invalid_key = b"-----BEGIN PRIVATE KEY-----\nInvalid\n-----END PRIVATE KEY-----"

    with pytest.raises(ValueError):
        cryptography.rsa_decrypt_aes_key(encrypted_key, invalid_key)


def test_rsa_decrypt_aes_key_wrong_key():
    """Test that decrypting with wrong private key fails."""
    private_key_pem_1, public_key_pem_1 = cryptography.generate_rsa_key_pair()
    private_key_pem_2, _ = cryptography.generate_rsa_key_pair()
    aes_key = cryptography.generate_aes_key()

    encrypted_key = cryptography.rsa_encrypt_aes_key(aes_key, public_key_pem_1)

    with pytest.raises(Exception):  # Should raise decryption error
        cryptography.rsa_decrypt_aes_key(encrypted_key, private_key_pem_2)


def test_rsa_encrypt_aes_key_with_ecdsa_key_raises_error():
    """Test that encrypting with an ECDSA key (not RSA) raises ValueError."""
    ecdsa_private_key, ecdsa_public_key = cryptography.generate_ecdsa_key_pair()
    aes_key = cryptography.generate_aes_key()

    with pytest.raises(ValueError, match="Public key must be an RSA key"):
        cryptography.rsa_encrypt_aes_key(aes_key, ecdsa_public_key)


def test_rsa_decrypt_aes_key_with_ecdsa_key_raises_error():
    """Test that decrypting with an ECDSA key (not RSA) raises ValueError."""
    ecdsa_private_key, _ = cryptography.generate_ecdsa_key_pair()
    encrypted_key = b"fake encrypted data"

    with pytest.raises(ValueError, match="Private key must be an RSA key"):
        cryptography.rsa_decrypt_aes_key(encrypted_key, ecdsa_private_key)


def test_aes_gcm_encrypt_decrypt_round_trip():
    """Test AES-GCM encryption and decryption round trip."""
    aes_key = cryptography.generate_aes_key()
    iv = cryptography.generate_iv()
    plaintext = b"Hello, World! This is test data."

    encrypted_data = cryptography.aes_gcm_encrypt(plaintext, aes_key, iv)
    decrypted_data = cryptography.aes_gcm_decrypt(encrypted_data, aes_key, iv)

    assert decrypted_data == plaintext
    assert encrypted_data != plaintext
    assert len(encrypted_data) == len(plaintext) + 16  # ciphertext + 16-byte tag


def test_aes_gcm_encrypt_decrypt_with_associated_data():
    """Test AES-GCM encryption and decryption with associated data."""
    aes_key = cryptography.generate_aes_key()
    iv = cryptography.generate_iv()
    plaintext = b"Test data"
    associated_data = b"Additional authenticated data"

    encrypted_data = cryptography.aes_gcm_encrypt(plaintext, aes_key, iv, associated_data)
    decrypted_data = cryptography.aes_gcm_decrypt(encrypted_data, aes_key, iv, associated_data)

    assert decrypted_data == plaintext


def test_aes_gcm_decrypt_wrong_associated_data():
    """Test that decrypting with wrong associated data fails."""
    aes_key = cryptography.generate_aes_key()
    iv = cryptography.generate_iv()
    plaintext = b"Test data"
    associated_data = b"Correct AAD"
    wrong_aad = b"Wrong AAD"

    encrypted_data = cryptography.aes_gcm_encrypt(plaintext, aes_key, iv, associated_data)

    with pytest.raises(Exception):  # Should raise authentication error
        cryptography.aes_gcm_decrypt(encrypted_data, aes_key, iv, wrong_aad)


def test_aes_gcm_encrypt_decrypt_various_data_sizes():
    """Test AES-GCM encryption/decryption with various data sizes."""
    aes_key = cryptography.generate_aes_key()
    iv = cryptography.generate_iv()

    test_cases = [
        b"",
        b"a",
        b"Short message",
        b"Medium length message with some content",
        b"Very long message " * 100,
    ]

    for plaintext in test_cases:
        encrypted_data = cryptography.aes_gcm_encrypt(plaintext, aes_key, iv)
        decrypted_data = cryptography.aes_gcm_decrypt(encrypted_data, aes_key, iv)
        assert decrypted_data == plaintext, f"Failed for data: {plaintext[:50]}"


def test_aes_gcm_encrypt_different_plaintexts():
    """Test that encrypting different plaintexts produces different ciphertexts."""
    aes_key = cryptography.generate_aes_key()
    iv = cryptography.generate_iv()

    plaintext_1 = b"First message"
    plaintext_2 = b"Second message"

    encrypted_1 = cryptography.aes_gcm_encrypt(plaintext_1, aes_key, iv)
    encrypted_2 = cryptography.aes_gcm_encrypt(plaintext_2, aes_key, iv)

    assert encrypted_1 != encrypted_2


def test_aes_gcm_encrypt_same_plaintext_different_ivs():
    """Test that encrypting same plaintext with different IVs produces different ciphertexts."""
    aes_key = cryptography.generate_aes_key()
    iv_1 = cryptography.generate_iv()
    iv_2 = cryptography.generate_iv()
    plaintext = b"Same message"

    encrypted_1 = cryptography.aes_gcm_encrypt(plaintext, aes_key, iv_1)
    encrypted_2 = cryptography.aes_gcm_encrypt(plaintext, aes_key, iv_2)

    assert encrypted_1 != encrypted_2


def test_aes_gcm_decrypt_wrong_key():
    """Test that decrypting with wrong key fails."""
    aes_key_1 = cryptography.generate_aes_key()
    aes_key_2 = cryptography.generate_aes_key()
    iv = cryptography.generate_iv()
    plaintext = b"Test data"

    encrypted_data = cryptography.aes_gcm_encrypt(plaintext, aes_key_1, iv)

    with pytest.raises(Exception):  # Should raise authentication error
        cryptography.aes_gcm_decrypt(encrypted_data, aes_key_2, iv)


def test_aes_gcm_decrypt_wrong_iv():
    """Test that decrypting with wrong IV fails."""
    aes_key = cryptography.generate_aes_key()
    iv_1 = cryptography.generate_iv()
    iv_2 = cryptography.generate_iv()
    plaintext = b"Test data"

    encrypted_data = cryptography.aes_gcm_encrypt(plaintext, aes_key, iv_1)

    with pytest.raises(Exception):  # Should raise authentication error
        cryptography.aes_gcm_decrypt(encrypted_data, aes_key, iv_2)


def test_aes_gcm_decrypt_corrupted_data():
    """Test that decrypting corrupted data fails."""
    aes_key = cryptography.generate_aes_key()
    iv = cryptography.generate_iv()
    plaintext = b"Test data"

    encrypted_data = cryptography.aes_gcm_encrypt(plaintext, aes_key, iv)
    # Corrupt the data
    corrupted_data = encrypted_data[:-1] + b"\x00"

    with pytest.raises(Exception):  # Should raise authentication error
        cryptography.aes_gcm_decrypt(corrupted_data, aes_key, iv)


def test_aes_gcm_encrypt_invalid_key_size():
    """Test that encrypting with invalid key size raises ValueError."""
    invalid_key = b"invalid" * 4  # 28 bytes, not 32
    iv = cryptography.generate_iv()
    plaintext = b"Test data"

    with pytest.raises(ValueError, match="AES key must be 32 bytes"):
        cryptography.aes_gcm_encrypt(plaintext, invalid_key, iv)


def test_aes_gcm_decrypt_invalid_key_size():
    """Test that decrypting with invalid key size raises ValueError."""
    invalid_key = b"invalid" * 4  # 28 bytes, not 32
    iv = cryptography.generate_iv()
    encrypted_data = b"fake encrypted data" + b"\x00" * 16  # Add fake tag

    with pytest.raises(ValueError, match="AES key must be 32 bytes"):
        cryptography.aes_gcm_decrypt(encrypted_data, invalid_key, iv)


def test_aes_gcm_encrypt_invalid_iv_size():
    """Test that encrypting with invalid IV size raises ValueError."""
    aes_key = cryptography.generate_aes_key()
    invalid_iv = b"invalid"  # 7 bytes, not 12
    plaintext = b"Test data"

    with pytest.raises(ValueError, match="IV must be 12 bytes"):
        cryptography.aes_gcm_encrypt(plaintext, aes_key, invalid_iv)


def test_aes_gcm_decrypt_invalid_iv_size():
    """Test that decrypting with invalid IV size raises ValueError."""
    aes_key = cryptography.generate_aes_key()
    invalid_iv = b"invalid"  # 7 bytes, not 12
    encrypted_data = b"fake encrypted data" + b"\x00" * 16  # Add fake tag

    with pytest.raises(ValueError, match="IV must be 12 bytes"):
        cryptography.aes_gcm_decrypt(encrypted_data, aes_key, invalid_iv)


def test_aes_gcm_decrypt_too_short_data():
    """Test that decrypting data that's too short raises ValueError."""
    aes_key = cryptography.generate_aes_key()
    iv = cryptography.generate_iv()
    short_data = b"short"  # Less than 16 bytes (no tag)

    with pytest.raises(ValueError, match="Encrypted data too short"):
        cryptography.aes_gcm_decrypt(short_data, aes_key, iv)


def test_pbkdf2_derive_key_from_pin():
    """Test PBKDF2 key derivation from PIN."""
    pin = "1234"
    salt = cryptography.generate_iv(iv_size=16)
    iterations = 100000

    derived_key = cryptography.pbkdf2_derive_key_from_pin(pin, salt, iterations)

    assert isinstance(derived_key, bytes)
    assert len(derived_key) == 32  # Default key size


def test_pbkdf2_derive_key_from_pin_custom_size():
    """Test PBKDF2 key derivation with custom key size."""
    pin = "123456"
    salt = cryptography.generate_iv(iv_size=16)
    iterations = 100000

    derived_key = cryptography.pbkdf2_derive_key_from_pin(pin, salt, iterations, key_size=16)

    assert isinstance(derived_key, bytes)
    assert len(derived_key) == 16


def test_pbkdf2_derive_key_from_pin_different_salts():
    """Test that different salts produce different keys."""
    pin = "1234"
    salt_1 = cryptography.generate_iv(iv_size=16)
    salt_2 = cryptography.generate_iv(iv_size=16)
    iterations = 100000

    key_1 = cryptography.pbkdf2_derive_key_from_pin(pin, salt_1, iterations)
    key_2 = cryptography.pbkdf2_derive_key_from_pin(pin, salt_2, iterations)

    assert key_1 != key_2


def test_pbkdf2_derive_key_from_pin_different_pins():
    """Test that different PINs produce different keys."""
    pin_1 = "1234"
    pin_2 = "5678"
    salt = cryptography.generate_iv(iv_size=16)
    iterations = 100000

    key_1 = cryptography.pbkdf2_derive_key_from_pin(pin_1, salt, iterations)
    key_2 = cryptography.pbkdf2_derive_key_from_pin(pin_2, salt, iterations)

    assert key_1 != key_2


def test_pbkdf2_derive_key_from_pin_invalid_salt():
    """Test that empty salt raises ValueError."""
    pin = "1234"
    empty_salt = b""
    iterations = 100000

    with pytest.raises(ValueError, match="Salt must be at least 1 byte"):
        cryptography.pbkdf2_derive_key_from_pin(pin, empty_salt, iterations)


def test_pbkdf2_encrypt_decrypt_aes_key_round_trip():
    """Test PBKDF2 encryption and decryption of AES key round trip."""
    aes_key = cryptography.generate_aes_key()
    pin = "1234"

    encrypted_key, salt, iv = cryptography.pbkdf2_encrypt_aes_key(aes_key, pin)
    decrypted_key = cryptography.pbkdf2_decrypt_aes_key(encrypted_key, pin, salt, iv)

    assert decrypted_key == aes_key
    assert encrypted_key != aes_key
    assert isinstance(salt, bytes)
    assert len(salt) == 16
    assert isinstance(iv, bytes)
    assert len(iv) == 12


def test_pbkdf2_encrypt_aes_key_custom_salt():
    """Test PBKDF2 encryption with custom salt."""
    aes_key = cryptography.generate_aes_key()
    pin = "123456"
    custom_salt = cryptography.generate_iv(iv_size=16)

    encrypted_key, salt, iv = cryptography.pbkdf2_encrypt_aes_key(aes_key, pin, salt=custom_salt)
    decrypted_key = cryptography.pbkdf2_decrypt_aes_key(encrypted_key, pin, salt, iv)

    assert decrypted_key == aes_key
    assert salt == custom_salt


def test_pbkdf2_decrypt_aes_key_wrong_pin():
    """Test that decrypting with wrong PIN fails."""
    aes_key = cryptography.generate_aes_key()
    pin = "1234"
    wrong_pin = "5678"

    encrypted_key, salt, iv = cryptography.pbkdf2_encrypt_aes_key(aes_key, pin)

    with pytest.raises(ValueError, match="Failed to decrypt AES key"):
        cryptography.pbkdf2_decrypt_aes_key(encrypted_key, wrong_pin, salt, iv)


def test_pbkdf2_decrypt_aes_key_wrong_salt():
    """Test that decrypting with wrong salt fails."""
    aes_key = cryptography.generate_aes_key()
    pin = "1234"

    encrypted_key, salt, iv = cryptography.pbkdf2_encrypt_aes_key(aes_key, pin)
    wrong_salt = cryptography.generate_iv(iv_size=16)

    with pytest.raises(ValueError, match="Failed to decrypt AES key"):
        cryptography.pbkdf2_decrypt_aes_key(encrypted_key, pin, wrong_salt, iv)


def test_pbkdf2_encrypt_aes_key_invalid_key_size():
    """Test that encrypting with invalid AES key size raises ValueError."""
    invalid_key = b"invalid" * 4  # 28 bytes, not 32
    pin = "1234"

    with pytest.raises(ValueError, match="AES key must be 32 bytes"):
        cryptography.pbkdf2_encrypt_aes_key(invalid_key, pin)


def test_pbkdf2_encrypt_decrypt_aes_key_different_iterations():
    """Test that same PIN with different iterations produces different keys."""
    aes_key = cryptography.generate_aes_key()
    pin = "1234"
    salt = cryptography.generate_iv(iv_size=16)

    encrypted_key_1, salt_1, iv_1 = cryptography.pbkdf2_encrypt_aes_key(
        aes_key, pin, salt=salt, iterations=100000
    )
    encrypted_key_2, salt_2, iv_2 = cryptography.pbkdf2_encrypt_aes_key(
        aes_key, pin, salt=salt, iterations=200000
    )

    # Different iterations should produce different encrypted keys
    assert encrypted_key_1 != encrypted_key_2
    assert salt_1 == salt_2  # Same salt was provided

    # But both should decrypt correctly with their respective iterations
    decrypted_1 = cryptography.pbkdf2_decrypt_aes_key(encrypted_key_1, pin, salt_1, iv_1, iterations=100000)
    decrypted_2 = cryptography.pbkdf2_decrypt_aes_key(encrypted_key_2, pin, salt_2, iv_2, iterations=200000)

    assert decrypted_1 == aes_key
    assert decrypted_2 == aes_key


def test_hybrid_encryption_round_trip():
    """Test complete hybrid encryption (RSA for AES key, AES-GCM for data) round trip."""
    # Generate keys
    rsa_private_key, rsa_public_key = cryptography.generate_rsa_key_pair()
    aes_key = cryptography.generate_aes_key()
    iv = cryptography.generate_iv()
    plaintext = b"This is a test message for hybrid encryption."

    # Encrypt AES key with RSA
    encrypted_aes_key = cryptography.rsa_encrypt_aes_key(aes_key, rsa_public_key)

    # Encrypt data with AES-GCM
    encrypted_data = cryptography.aes_gcm_encrypt(plaintext, aes_key, iv)

    # Decrypt AES key with RSA
    decrypted_aes_key = cryptography.rsa_decrypt_aes_key(encrypted_aes_key, rsa_private_key)

    # Decrypt data with AES-GCM
    decrypted_data = cryptography.aes_gcm_decrypt(encrypted_data, decrypted_aes_key, iv)

    assert decrypted_data == plaintext
    assert decrypted_aes_key == aes_key
