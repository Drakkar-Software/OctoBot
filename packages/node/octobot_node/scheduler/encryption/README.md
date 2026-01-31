# Task Encryption Module

This module provides secure encryption and decryption functionality for task inputs and outputs in the OctoBot Node scheduler. It implements a hybrid encryption scheme combining RSA and AES-GCM to ensure both security and performance.

## Overview

The encryption module uses a **hybrid encryption approach with digital signatures** that combines:
- **RSA encryption** (4096-bit) for securely exchanging AES keys
- **AES-GCM encryption** (256-bit) for encrypting the actual task data
- **ECDSA signatures** (SECP256R1) for non-repudiation and authenticity verification

This approach leverages the strengths of all three cryptographic primitives:
- RSA provides secure key exchange without requiring a pre-shared secret
- AES-GCM provides fast, authenticated encryption for large data payloads
- ECDSA provides cryptographic signatures that cover both content and metadata, enabling verification without decryption

## Security Features

### 1. Hybrid Encryption
- **RSA (4096-bit)**: Used for secure key exchange
  - OAEP padding with SHA-256 for enhanced security
  - Prevents key exchange vulnerabilities
- **AES-GCM (256-bit)**: Used for data encryption
  - Authenticated encryption ensures data integrity
  - Fast encryption/decryption for large payloads

### 2. Digital Signatures (ECDSA)
- **ECDSA (SECP256R1)**: Used for cryptographic signatures
  - Provides non-repudiation and authenticity verification
  - Signatures cover the entire payload (encrypted content + encrypted AES key + IV)
  - Enables verification without decryption
  - Prevents tampering with both content and metadata

**How Signatures Work:**
1. During encryption, the signature is calculated on: `encrypted_content + encrypted_aes_key + iv`
2. The signature is stored in metadata alongside the encrypted AES key and IV
3. During decryption, the signature is verified before decrypting the content
4. If any part of the payload (content, AES key, or IV) is tampered with, signature verification fails
5. This ensures both the encrypted content and the metadata are authenticated

### 3. Unique Keys Per Encryption
- Each encryption operation generates a new random AES key
- Each encryption uses a unique initialization vector (IV)
- Prevents pattern analysis and ensures forward secrecy

### 4. Authenticated Encryption
- AES-GCM provides built-in authentication
- Detects tampering or corruption of encrypted data
- Ensures data integrity without additional MAC

### 5. Secure Key Storage
- AES keys are never stored in plaintext
- AES keys are encrypted with RSA before storage/transmission
- Only encrypted keys, IVs, and signatures are stored in metadata

### 6. Separation of Concerns
- Different RSA and ECDSA key pairs for inputs and outputs
- Allows different security policies for different data flows
- Enables key rotation without affecting both directions

## Security Guarantees

1. **Confidentiality**: Encrypted data cannot be read without the private key
2. **Integrity**: Any tampering with encrypted data or metadata will be detected
3. **Non-Repudiation**: Digital signatures provide cryptographic proof of origin
4. **Forward Secrecy**: Compromising one encryption doesn't affect others (unique keys per operation)
5. **Key Security**: AES keys are protected by RSA encryption
6. **Authentication**: AES-GCM and ECDSA signatures ensure data authenticity
7. **Metadata Protection**: Signatures cover both content and metadata, preventing tampering

## Error Handling

The module defines specific exceptions for different error scenarios:

- `MissingMetadataError`: Raised when metadata is missing or incomplete
- `MetadataParsingError`: Raised when metadata JSON cannot be parsed or base64 decoding fails
- `EncryptionTaskError`: Raised when encryption/decryption operations fail
- `SignatureVerificationError`: Raised when signature verification fails

## Available Functions

The module provides four main functions for encrypting and decrypting task data:

### Task Inputs
- `encrypt_task_content(content: str) -> Tuple[str, str]`: Encrypts task input content
- `decrypt_task_content(content: str, metadata: Optional[str]) -> str`: Decrypts task input content

### Task Outputs
- `encrypt_task_result(result: str) -> Tuple[str, str]`: Encrypts task output result
- `decrypt_task_result(encrypted_result: str, metadata: Optional[str]) -> str`: Decrypts task output result

## Usage Examples

### Encrypting Task Inputs

```python
from octobot_node.scheduler.encryption import encrypt_task_content

# Encrypt task input content
content = '{"action": "buy", "symbol": "BTC/USD", "amount": 0.1}'
encrypted_content, metadata = encrypt_task_content(content)

# Store both encrypted_content and metadata
# metadata must be preserved for decryption
```

### Decrypting Task Inputs

```python
from octobot_node.scheduler.encryption import decrypt_task_content
from octobot_node.scheduler.encryption import (
    MissingMetadataError,
    EncryptionTaskError,
    SignatureVerificationError
)

# Decrypt task content
try:
    decrypted_content = decrypt_task_content(encrypted_content, metadata)
    # Use decrypted_content...
except MissingMetadataError as e:
    # Handle missing metadata
except SignatureVerificationError as e:
    # Handle signature verification failure
except EncryptionTaskError as e:
    # Handle decryption failure
```

### Encrypting Task Outputs

```python
from octobot_node.scheduler.encryption import encrypt_task_result

# Encrypt a task result
result = '{"status": "success", "data": "sensitive information"}'
encrypted_result, metadata = encrypt_task_result(result)

# Store both encrypted_result and metadata
# metadata must be preserved for decryption
```

### Decrypting Task Outputs

```python
from octobot_node.scheduler.encryption import decrypt_task_result
from octobot_node.scheduler.encryption import (
    MissingMetadataError,
    EncryptionTaskError,
    SignatureVerificationError
)

# Decrypt task result
try:
    decrypted_result = decrypt_task_result(encrypted_result, metadata)
    # Use decrypted_result...
except MissingMetadataError as e:
    # Handle missing metadata
except SignatureVerificationError as e:
    # Handle signature verification failure
except EncryptionTaskError as e:
    # Handle decryption failure
```

## Key Management

### Configuration Keys

The system uses separate RSA and ECDSA key pairs for task inputs and outputs:

**Task Inputs:**
- `TASKS_INPUTS_RSA_PUBLIC_KEY`: RSA public key for encrypting AES keys in task inputs
- `TASKS_INPUTS_RSA_PRIVATE_KEY`: RSA private key for decrypting AES keys in task inputs
- `TASKS_INPUTS_ECDSA_PUBLIC_KEY`: ECDSA public key for verifying signatures on task inputs
- `TASKS_INPUTS_ECDSA_PRIVATE_KEY`: ECDSA private key for signing task inputs

**Task Outputs:**
- `TASKS_OUTPUTS_RSA_PUBLIC_KEY`: RSA public key for encrypting AES keys in task outputs
- `TASKS_OUTPUTS_RSA_PRIVATE_KEY`: RSA private key for decrypting AES keys in task outputs
- `TASKS_OUTPUTS_ECDSA_PUBLIC_KEY`: ECDSA public key for verifying signatures on task outputs
- `TASKS_OUTPUTS_ECDSA_PRIVATE_KEY`: ECDSA private key for signing task outputs

### Key Generation

RSA key pairs can be generated using:
```python
from octobot_commons.cryptography import generate_rsa_key_pair

# Generate a 4096-bit RSA key pair
private_key_pem, public_key_pem = generate_rsa_key_pair(key_size=4096)
```

ECDSA key pairs can be generated using:
```python
from octobot_commons.cryptography import generate_ecdsa_key_pair

# Generate an ECDSA key pair (SECP256R1 by default)
private_key_pem, public_key_pem = generate_ecdsa_key_pair()
```

### Configuration

Keys are configured via environment variables in the application settings:

```python
# In .env or environment variables
TASKS_INPUTS_RSA_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\n..."
TASKS_INPUTS_RSA_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n..."
TASKS_INPUTS_ECDSA_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\n..."
TASKS_INPUTS_ECDSA_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n..."
TASKS_OUTPUTS_RSA_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\n..."
TASKS_OUTPUTS_RSA_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n..."
TASKS_OUTPUTS_ECDSA_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\n..."
TASKS_OUTPUTS_ECDSA_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n..."
```

**Note**: If keys are not configured (`None`), encryption/decryption is skipped and tasks operate in plaintext mode. This allows for development and testing without encryption overhead.

## Best Practices

1. **Key Management**:
   - Store private keys securely (environment variables, secret management systems)
   - Never commit keys to version control
   - Rotate keys periodically
   - Use different keys for different environments (dev, staging, production)
   - Keep RSA and ECDSA key pairs separate for different purposes

2. **Metadata Handling**:
   - Always store metadata alongside encrypted data
   - Metadata includes encrypted AES key, IV, and signature (all base64-encoded)
   - Signatures ensure metadata integrity
   - Include metadata in backups

3. **Error Handling**:
   - Always handle encryption/decryption errors gracefully
   - Handle `SignatureVerificationError` separately from other errors
   - Log errors without exposing sensitive information
   - Fail securely (don't fall back to plaintext on error)

4. **Performance**:
   - Encryption is optional (can be disabled by not setting keys)
   - Consider performance impact for high-throughput scenarios
   - Monitor encryption/decryption performance
   - ECDSA signing/verification is fast (~1-2ms per operation)

## Why This Approach is Secure

1. **Industry-Standard Algorithms**: Uses well-vetted cryptographic algorithms (RSA-OAEP, AES-GCM, ECDSA)

2. **Proper Key Sizes**: 
   - RSA 4096-bit keys provide strong security
   - AES 256-bit keys are considered secure for the foreseeable future
   - ECDSA SECP256R1 provides strong signature security

3. **Secure Padding**: RSA-OAEP padding prevents various attacks (e.g., padding oracle attacks)

4. **Authenticated Encryption**: AES-GCM provides both encryption and authentication in one operation

5. **Digital Signatures**: ECDSA signatures provide non-repudiation and enable verification without decryption

6. **Comprehensive Protection**: Signatures cover both content and metadata, preventing tampering with encrypted AES keys or IVs

7. **Key Isolation**: Each encryption uses unique keys, limiting the impact of key compromise

8. **No Key Reuse**: Random key generation prevents key reuse vulnerabilities

9. **Separation of Keys**: Different keys for inputs/outputs allow independent key management

## Limitations and Considerations

1. **Performance**: 
   - RSA encryption/decryption is slower than symmetric encryption (mitigated by hybrid approach)
   - ECDSA signing/verification adds minimal overhead (~1-2ms per operation)

2. **Key Distribution**: 
   - Public keys must be securely distributed to encrypting nodes
   - ECDSA public keys must be distributed for signature verification

3. **Key Storage**: 
   - Private keys must be securely stored and protected
   - Both RSA and ECDSA private keys require secure storage

4. **Metadata Size**: 
   - Metadata adds overhead (encrypted AES key + IV + signature, all base64-encoded)
   - Typical metadata size: ~600-800 bytes

5. **Optional Encryption**: 
   - System can operate without encryption if keys are not configured (useful for development)
   - Signature verification is skipped if ECDSA keys are not configured
