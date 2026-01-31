# pylint: disable=R0801
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

import secrets
from typing import Optional, Tuple

from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend


def generate_rsa_key_pair(key_size: int = 4096) -> Tuple[bytes, bytes]:
    """Generate an RSA key pair

    This function generates a private and public RSA key pair equivalent to:
    - openssl genrsa -out user_private_key.pem 4096
    - openssl rsa -in user_private_key.pem -pubout -out user_public_key.pem

    :param key_size: The size of the RSA key in bits. Defaults to 4096.
    :type key_size: int
    :return: A tuple containing (private_key_pem, public_key_pem) as bytes.
    :rtype: Tuple[bytes, bytes]
    :raises ValueError: If key_size is less than 2048 bits (security best practice).
    """
    if key_size < 2048:
        raise ValueError("RSA key size must be at least 2048 bits for security.")

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
    )

    # Serialize private key to PEM format
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )

    # Extract and serialize public key to PEM format
    public_key = private_key.public_key()
    public_key_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    return private_key_pem, public_key_pem


def generate_aes_key(key_size: int = 32) -> bytes:
    """Generate a random AES key

    This function generates random bytes equivalent to:
    - openssl rand -out aes_key_s1.bin 32

    :param key_size: The size of the AES key in bytes. Defaults to 32 (256 bits).
    :type key_size: int
    :return: Random bytes suitable for use as an AES key.
    :rtype: bytes
    :raises ValueError: If key_size is less than 1.
    """
    if key_size < 1:
        raise ValueError("Key size must be at least 1 byte.")

    return secrets.token_bytes(key_size)


def generate_iv(iv_size: int = 12) -> bytes:
    """Generate a random initialization vector (IV)

    This function generates random bytes equivalent to:
    - openssl rand -out iv_s1.bin 12

    :param iv_size: The size of the IV in bytes. Defaults to 12 (standard for AES-GCM).
    :type iv_size: int
    :return: Random bytes suitable for use as an IV.
    :rtype: bytes
    :raises ValueError: If iv_size is less than 1.
    """
    if iv_size < 1:
        raise ValueError("IV size must be at least 1 byte.")

    return secrets.token_bytes(iv_size)


def rsa_decrypt_aes_key(encrypted_aes_key: bytes, private_key_pem: bytes) -> bytes:
    """Decrypt an RSA-encrypted AES key

    This function decrypts an AES key equivalent to:
    - openssl rsautl -decrypt -in aes_key.enc -oaep -inkey private_key.pem -out aes_key.bin

    :param encrypted_aes_key: The RSA-encrypted AES key.
    :type encrypted_aes_key: bytes
    :param private_key_pem: The RSA private key in PEM format.
    :type private_key_pem: bytes
    :return: The decrypted AES key as bytes.
    :rtype: bytes
    :raises ValueError: If the private key cannot be loaded or is invalid.
    """
    # Load the private key from PEM format
    private_key = serialization.load_pem_private_key(
        private_key_pem,
        password=None,
    )

    if not isinstance(private_key, rsa.RSAPrivateKey):
        raise ValueError("Private key must be an RSA key.")

    # Decrypt using OAEP padding
    decrypted_key = private_key.decrypt(
        encrypted_aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    return decrypted_key


def rsa_encrypt_aes_key(aes_key: bytes, public_key_pem: bytes) -> bytes:
    """Encrypt an AES key using RSA public key

    This function encrypts an AES key equivalent to:
    - openssl rsautl -encrypt -in aes_key.bin -oaep -pubin -inkey public_key.pem -out aes_key.enc

    :param aes_key: The AES key to encrypt.
    :type aes_key: bytes
    :param public_key_pem: The RSA public key in PEM format.
    :type public_key_pem: bytes
    :return: The encrypted AES key as bytes.
    :rtype: bytes
    :raises ValueError: If the public key cannot be loaded or is invalid.
    """
    # Load the public key from PEM format
    public_key = serialization.load_pem_public_key(public_key_pem)

    if not isinstance(public_key, rsa.RSAPublicKey):
        raise ValueError("Public key must be an RSA key.")

    # Encrypt using OAEP padding
    encrypted_key = public_key.encrypt(
        aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    return encrypted_key


def aes_gcm_decrypt(
    encrypted_data: bytes,
    aes_key: bytes,
    iv: bytes,
    associated_data: Optional[bytes] = None,
) -> bytes:
    """Decrypt data using AES-256-GCM

    This function decrypts data equivalent to:
    - openssl enc -aes-256-gcm -d -in data.enc -out data.bin -K $AES_KEY -iv $IV

    :param encrypted_data: The encrypted data (ciphertext + authentication tag).
    :type encrypted_data: bytes
    :param aes_key: The AES key (32 bytes for AES-256).
    :type aes_key: bytes
    :param iv: The initialization vector (12 bytes for AES-GCM).
    :type iv: bytes
    :param associated_data: Optional associated data (AAD) for authenticated encryption.
    :type associated_data: Optional[bytes]
    :return: The decrypted plaintext data.
    :rtype: bytes
    :raises ValueError: If key or IV sizes are invalid.
    """
    if len(aes_key) != 32:
        raise ValueError("AES key must be 32 bytes (256 bits) for AES-256-GCM.")

    if len(iv) != 12:
        raise ValueError("IV must be 12 bytes for AES-GCM.")

    # AESGCM expects the authentication tag to be appended to the ciphertext
    # OpenSSL GCM format: ciphertext + 16-byte tag
    if len(encrypted_data) < 16:
        raise ValueError(
            "Encrypted data too short (must include 16-byte authentication tag)."
        )

    # Create AESGCM cipher
    aesgcm = AESGCM(aes_key)

    # Decrypt with authentication (encrypted_data should be ciphertext + 16-byte tag)
    plaintext = aesgcm.decrypt(iv, encrypted_data, associated_data)

    return plaintext


def aes_gcm_encrypt(
    plaintext: bytes, aes_key: bytes, iv: bytes, associated_data: Optional[bytes] = None
) -> bytes:
    """Encrypt data using AES-256-GCM

    This function encrypts data equivalent to:
    - openssl enc -aes-256-gcm -in data.bin -out data.enc -K $AES_KEY -iv $IV

    :param plaintext: The plaintext data to encrypt.
    :type plaintext: bytes
    :param aes_key: The AES key (32 bytes for AES-256).
    :type aes_key: bytes
    :param iv: The initialization vector (12 bytes for AES-GCM).
    :type iv: bytes
    :param associated_data: Optional associated data (AAD) for authenticated encryption.
    :type associated_data: Optional[bytes]
    :return: The encrypted data (ciphertext + 16-byte authentication tag).
    :rtype: bytes
    :raises ValueError: If key or IV sizes are invalid.
    """
    if len(aes_key) != 32:
        raise ValueError("AES key must be 32 bytes (256 bits) for AES-256-GCM.")

    if len(iv) != 12:
        raise ValueError("IV must be 12 bytes for AES-GCM.")

    # Create AESGCM cipher
    aesgcm = AESGCM(aes_key)

    # Encrypt with authentication (returns ciphertext + tag)
    ciphertext_with_tag = aesgcm.encrypt(iv, plaintext, associated_data)

    return ciphertext_with_tag


def pbkdf2_derive_key_from_pin(
    pin: str, salt: bytes, iterations: int = 200000, key_size: int = 32
) -> bytes:
    """Derive a cryptographic key from a PIN using PBKDF2

    This function derives a key from a user PIN using PBKDF2-HMAC-SHA256.
    High iteration count is recommended for PINs due to their low entropy.

    :param pin: The user PIN (4-6 digits recommended).
    :type pin: str
    :param salt: Random salt bytes (should be unique per encryption, 16 bytes recommended).
    :type salt: bytes
    :param iterations: Number of PBKDF2 iterations. Defaults to 200000 (high for PIN security).
    :type iterations: int
    :param key_size: Size of the derived key in bytes. Defaults to 32 (256 bits for AES-256).
    :type key_size: int
    :return: The derived key as bytes.
    :rtype: bytes
    :raises ValueError: If salt is empty or iterations/key_size are invalid.
    """
    if len(salt) < 1:
        raise ValueError("Salt must be at least 1 byte.")
    if iterations < 1:
        raise ValueError("Iterations must be at least 1.")
    if key_size < 1:
        raise ValueError("Key size must be at least 1 byte.")

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=key_size,
        salt=salt,
        iterations=iterations,
        backend=default_backend(),
    )
    return kdf.derive(pin.encode("utf-8"))


def pbkdf2_encrypt_aes_key(
    aes_key: bytes,
    pin: str,
    salt: Optional[bytes] = None,
    iterations: int = 200000,
) -> Tuple[bytes, bytes, bytes]:
    """Encrypt an AES key using a PIN-derived key via PBKDF2

    This function encrypts an AES key using a key derived from a user PIN.
    The salt and IV are generated randomly and must be stored for decryption.

    :param aes_key: The AES key to encrypt (32 bytes for AES-256).
    :type aes_key: bytes
    :param pin: The user PIN (4-6 digits recommended).
    :type pin: str
    :param salt: Optional salt bytes. If None, a random 16-byte salt is generated.
    :type salt: Optional[bytes]
    :param iterations: Number of PBKDF2 iterations. Defaults to 200000.
    :type iterations: int
    :return: A tuple containing (encrypted_key, salt, iv).
    :rtype: Tuple[bytes, bytes, bytes]
    :raises ValueError: If AES key size is invalid.
    """
    if len(aes_key) != 32:
        raise ValueError("AES key must be 32 bytes (256 bits) for AES-256.")

    if salt is None:
        salt = secrets.token_bytes(16)

    # Derive key from PIN
    derived_key = pbkdf2_derive_key_from_pin(pin, salt, iterations, key_size=32)

    # Generate IV for AES-GCM
    iv = generate_iv()

    # Encrypt AES key using derived key
    encrypted_key = aes_gcm_encrypt(aes_key, derived_key, iv)

    return encrypted_key, salt, iv


def pbkdf2_decrypt_aes_key(
    encrypted_aes_key: bytes, pin: str, salt: bytes, iv: bytes, iterations: int = 200000
) -> bytes:
    """Decrypt an AES key using a PIN-derived key via PBKDF2

    This function decrypts an AES key that was encrypted with pbkdf2_encrypt_aes_key.

    :param encrypted_aes_key: The encrypted AES key.
    :type encrypted_aes_key: bytes
    :param pin: The user PIN used for encryption.
    :type pin: str
    :param salt: The salt used during encryption.
    :type salt: bytes
    :param iv: The IV used during encryption.
    :type iv: bytes
    :param iterations: Number of PBKDF2 iterations (must match encryption). Defaults to 200000.
    :type iterations: int
    :return: The decrypted AES key as bytes.
    :rtype: bytes
    :raises ValueError: If decryption fails (wrong PIN, corrupted data, etc.).
    """
    # Derive key from PIN (same parameters as encryption)
    derived_key = pbkdf2_derive_key_from_pin(pin, salt, iterations, key_size=32)

    # Decrypt AES key using derived key
    try:
        decrypted_key = aes_gcm_decrypt(encrypted_aes_key, derived_key, iv)
    except Exception as e:
        raise ValueError(
            "Failed to decrypt AES key. Wrong PIN or corrupted data."
        ) from e

    return decrypted_key
