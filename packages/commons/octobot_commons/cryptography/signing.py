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

from typing import Tuple, Optional
from cryptography.exceptions import InvalidSignature

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization


def generate_ecdsa_key_pair(
    curve: Optional[ec.EllipticCurve] = None,
) -> Tuple[bytes, bytes]:
    """Generate an ECDSA key pair

    This function generates a private and public ECDSA key pair equivalent to:
    - openssl ecparam -name secp256r1 -genkey -out user_ecdsa_private_key.pem
    - openssl ec -in user_ecdsa_private_key.pem -pubout -out user_ecdsa_public_key.pem

    :param curve: The elliptic curve to use. Defaults to SECP256R1 (secp256r1/prime256v1).
    :type curve: Optional[ec.EllipticCurve]
    :return: A tuple containing (private_key_pem, public_key_pem) as bytes.
    :rtype: Tuple[bytes, bytes]
    """
    if curve is None:
        curve = ec.SECP256R1()

    # Generate private key
    private_key = ec.generate_private_key(curve)

    # Serialize private key to PEM format
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    # Extract and serialize public key to PEM format
    public_key = private_key.public_key()
    public_key_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    return private_key_pem, public_key_pem


def sign_data(data: bytes, private_key_pem: bytes) -> bytes:
    """Generate an ECDSA signature for data

    This function generates a signature equivalent to:
    - openssl dgst -sha256 -sign ecdsa_private_key.pem -out signature.bin data.bin

    :param data: The data to sign.
    :type data: bytes
    :param private_key_pem: The ECDSA private key in PEM format.
    :type private_key_pem: bytes
    :return: The signature as bytes.
    :rtype: bytes
    :raises ValueError: If the private key cannot be loaded or is invalid.
    """
    # Load the private key from PEM format
    private_key = serialization.load_pem_private_key(
        private_key_pem,
        password=None,
    )

    if not isinstance(private_key, ec.EllipticCurvePrivateKey):
        raise ValueError("Private key must be an ECDSA key.")

    # Hash the data with SHA-256 and sign it
    signature = private_key.sign(data, ec.ECDSA(hashes.SHA256()))

    return signature


def verify_signature(data: bytes, public_key_pem: bytes, signature: bytes) -> bool:
    """Verify an ECDSA signature for data

    This function verifies a signature equivalent to:
    - openssl dgst -sha256 -verify ecdsa_public_key.pem -signature signature.bin data.bin

    :param data: The original data that was signed.
    :type data: bytes
    :param public_key_pem: The ECDSA public key in PEM format.
    :type public_key_pem: bytes
    :param signature: The signature to verify.
    :type signature: bytes
    :return: True if the signature is valid, False otherwise.
    :rtype: bool
    :raises ValueError: If the public key cannot be loaded or is invalid.
    """
    # Load the public key from PEM format
    public_key = serialization.load_pem_public_key(public_key_pem)

    if not isinstance(public_key, ec.EllipticCurvePublicKey):
        raise ValueError("Public key must be an ECDSA key.")

    try:
        # Hash the data with SHA-256 and verify the signature
        public_key.verify(signature, data, ec.ECDSA(hashes.SHA256()))
        return True
    except InvalidSignature:
        return False
