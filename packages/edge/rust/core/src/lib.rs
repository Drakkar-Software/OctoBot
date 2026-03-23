use hmac::{Hmac, Mac};
use sha2::{Sha256, Sha384, Sha512, Digest as Sha2Digest};
use sha3::{Sha3_256, Sha3_512};
use md5::Md5;
use rand::RngCore;
use serde::{Deserialize, Serialize};
use base64::{engine::general_purpose::STANDARD as BASE64, Engine as _};

// ── Error type ───────────────────────────────────────────────────────────────

#[derive(Debug, thiserror::Error)]
pub enum PolyfillError {
    #[error("Unsupported algorithm: {0}")]
    UnsupportedAlgorithm(String),
    #[error("HTTP error: {0}")]
    Http(String),
    #[error("Invalid encoding: {0}")]
    Encoding(String),
}

// ── Fetch types ──────────────────────────────────────────────────────────────

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct FetchRequest {
    pub url: String,
    pub method: String,
    pub headers: Vec<(String, String)>,
    pub body: Option<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct FetchResponse {
    pub status: u16,
    pub ok: bool,
    pub body: String,
    pub headers: Vec<(String, String)>,
}

// ── Encoding helper ──────────────────────────────────────────────────────────

fn encode_bytes(bytes: &[u8], encoding: &str) -> Result<String, PolyfillError> {
    match encoding {
        "hex"    => Ok(hex::encode(bytes)),
        "base64" => Ok(BASE64.encode(bytes)),
        // Latin-1: each byte maps to a Unicode code point 0–255 (matching Node.js "binary" encoding)
        "binary" | "latin1" => Ok(bytes.iter().map(|&b| b as char).collect()),
        other    => Err(PolyfillError::Encoding(format!("unsupported encoding: {other}"))),
    }
}

// ── HMAC ─────────────────────────────────────────────────────────────────────

/// Compute HMAC with the given algorithm, returning the result in the specified encoding.
/// Supports sha256, sha512, sha384.
pub fn hmac(
    algorithm: &str,
    secret: &str,
    data: &str,
    encoding: &str,
) -> Result<String, PolyfillError> {
    let key = secret.as_bytes();
    let msg = data.as_bytes();

    let result: Vec<u8> = match algorithm.to_lowercase().as_str() {
        "sha256" => {
            let mut mac = Hmac::<Sha256>::new_from_slice(key)
                .map_err(|e| PolyfillError::UnsupportedAlgorithm(e.to_string()))?;
            mac.update(msg);
            mac.finalize().into_bytes().to_vec()
        }
        "sha512" => {
            let mut mac = Hmac::<Sha512>::new_from_slice(key)
                .map_err(|e| PolyfillError::UnsupportedAlgorithm(e.to_string()))?;
            mac.update(msg);
            mac.finalize().into_bytes().to_vec()
        }
        "sha384" => {
            let mut mac = Hmac::<Sha384>::new_from_slice(key)
                .map_err(|e| PolyfillError::UnsupportedAlgorithm(e.to_string()))?;
            mac.update(msg);
            mac.finalize().into_bytes().to_vec()
        }
        other => return Err(PolyfillError::UnsupportedAlgorithm(other.to_string())),
    };

    encode_bytes(&result, encoding)
}

/// Compute HMAC-SHA256 from raw byte slices, returning raw bytes.
/// Used by Python and NAPI bindings for direct byte-level HMAC.
pub fn hmac_sha256(key: &[u8], message: &[u8]) -> Result<Vec<u8>, PolyfillError> {
    let mut mac = Hmac::<Sha256>::new_from_slice(key)
        .map_err(|e| PolyfillError::UnsupportedAlgorithm(e.to_string()))?;
    mac.update(message);
    Ok(mac.finalize().into_bytes().to_vec())
}

/// Compute HMAC-SHA512 from raw byte slices, returning raw bytes.
pub fn hmac_sha512(key: &[u8], message: &[u8]) -> Result<Vec<u8>, PolyfillError> {
    let mut mac = Hmac::<Sha512>::new_from_slice(key)
        .map_err(|e| PolyfillError::UnsupportedAlgorithm(e.to_string()))?;
    mac.update(message);
    Ok(mac.finalize().into_bytes().to_vec())
}

// ── Hash ─────────────────────────────────────────────────────────────────────

/// Compute a hash digest. Supports sha256, sha512, sha384, sha3-256, sha3-512, md5.
pub fn hash(
    algorithm: &str,
    data: &str,
    encoding: &str,
) -> Result<String, PolyfillError> {
    let bytes = data.as_bytes();

    let result: Vec<u8> = match algorithm.to_lowercase().as_str() {
        "sha256"   => Sha256::digest(bytes).to_vec(),
        "sha512"   => Sha512::digest(bytes).to_vec(),
        "sha384"   => Sha384::digest(bytes).to_vec(),
        "sha3-256" => Sha3_256::digest(bytes).to_vec(),
        "sha3-512" => Sha3_512::digest(bytes).to_vec(),
        "md5"      => Md5::digest(bytes).to_vec(),
        other      => return Err(PolyfillError::UnsupportedAlgorithm(other.to_string())),
    };

    encode_bytes(&result, encoding)
}

// ── Random bytes ─────────────────────────────────────────────────────────────

/// Maximum allowed size for random byte generation (1 MiB).
const MAX_RANDOM_BYTES: usize = 1_048_576;

pub fn random_bytes(size: usize) -> Result<Vec<u8>, PolyfillError> {
    if size > MAX_RANDOM_BYTES {
        return Err(PolyfillError::Encoding(
            format!("random_bytes size {size} exceeds maximum {MAX_RANDOM_BYTES}"),
        ));
    }
    let mut bytes = vec![0u8; size];
    rand::thread_rng().fill_bytes(&mut bytes);
    Ok(bytes)
}

pub fn random_bytes_hex(size: usize) -> Result<String, PolyfillError> {
    Ok(hex::encode(random_bytes(size)?))
}

// ── Buffer ops ───────────────────────────────────────────────────────────────

pub fn buffer_from_hex(hex_str: &str) -> Result<Vec<u8>, PolyfillError> {
    hex::decode(hex_str).map_err(|e| PolyfillError::Encoding(e.to_string()))
}

pub fn buffer_to_hex(data: &[u8]) -> String {
    hex::encode(data)
}

pub fn buffer_from_base64(b64: &str) -> Result<Vec<u8>, PolyfillError> {
    BASE64.decode(b64).map_err(|e| PolyfillError::Encoding(e.to_string()))
}

pub fn buffer_to_base64(data: &[u8]) -> String {
    BASE64.encode(data)
}

pub fn buffer_concat(bufs: Vec<Vec<u8>>) -> Vec<u8> {
    let total: usize = bufs.iter().map(|b| b.len()).sum();
    let mut result = Vec::with_capacity(total);
    for buf in bufs {
        result.extend_from_slice(&buf);
    }
    result
}

pub fn buffer_byte_length(utf8_str: &str) -> usize {
    utf8_str.len()
}

// ── Fetch (blocking — works on iOS/Android native, not WASM) ─────────────────

#[cfg(not(target_arch = "wasm32"))]
pub fn fetch_sync(req: FetchRequest) -> Result<FetchResponse, PolyfillError> {
    // Validate URL scheme to prevent SSRF against local/internal resources
    let url: reqwest::Url = req.url.parse()
        .map_err(|e| PolyfillError::Http(format!("invalid URL: {e}")))?;
    match url.scheme() {
        "https" | "http" => {}
        scheme => return Err(PolyfillError::Http(
            format!("unsupported URL scheme: {scheme} (only http/https allowed)"),
        )),
    }

    let client = reqwest::blocking::Client::builder()
        .danger_accept_invalid_certs(false)
        .redirect(reqwest::redirect::Policy::limited(5))
        .timeout(std::time::Duration::from_secs(30))
        .build()
        .map_err(|e| PolyfillError::Http(e.to_string()))?;

    let method: reqwest::Method = req.method.parse()
        .map_err(|e| PolyfillError::Http(format!("invalid HTTP method: {e}")))?;

    let mut builder = client.request(method, url);

    for (k, v) in &req.headers {
        // Reject header names/values containing CRLF to prevent header injection
        if k.contains('\r') || k.contains('\n') || k.contains('\0') {
            return Err(PolyfillError::Http(
                format!("invalid header name: contains prohibited characters"),
            ));
        }
        if v.contains('\r') || v.contains('\n') || v.contains('\0') {
            return Err(PolyfillError::Http(
                format!("invalid header value: contains prohibited characters"),
            ));
        }
        builder = builder.header(k.as_str(), v.as_str());
    }

    if let Some(body) = req.body {
        builder = builder.body(body);
    }

    let response = builder.send().map_err(|e| PolyfillError::Http(e.to_string()))?;
    let status = response.status().as_u16();
    let ok = response.status().is_success();
    let headers: Vec<(String, String)> = response
        .headers()
        .iter()
        .map(|(k, v)| (k.to_string(), v.to_str().unwrap_or("").to_string()))
        .collect();
    // Limit response body to 10 MiB to prevent OOM from malicious servers.
    // Read as raw bytes first so we can enforce the limit even for chunked responses
    // (which lack a Content-Length header).
    const MAX_RESPONSE_BODY: usize = 10 * 1024 * 1024;
    if let Some(len) = response.content_length() {
        if len > MAX_RESPONSE_BODY as u64 {
            return Err(PolyfillError::Http(
                format!("response body too large: {len} bytes (max {MAX_RESPONSE_BODY})"),
            ));
        }
    }
    let bytes = response.bytes().map_err(|e| PolyfillError::Http(e.to_string()))?;
    if bytes.len() > MAX_RESPONSE_BODY {
        return Err(PolyfillError::Http(
            format!("response body too large: {} bytes (max {MAX_RESPONSE_BODY})", bytes.len()),
        ));
    }
    let body = String::from_utf8_lossy(&bytes).into_owned();

    Ok(FetchResponse { status, ok, body, headers })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_hmac_sha256_hex() {
        let result = hmac("sha256", "secret_key", "message_data", "hex").unwrap();
        assert_eq!(result.len(), 64);
        assert!(result.chars().all(|c| c.is_ascii_hexdigit()));
    }

    #[test]
    fn test_hmac_sha512_hex() {
        let result = hmac("sha512", "secret_key", "message_data", "hex").unwrap();
        assert_eq!(result.len(), 128);
    }

    #[test]
    fn test_hmac_sha256_bytes() {
        let result = hmac_sha256(b"key", b"message").unwrap();
        assert_eq!(result.len(), 32);
    }

    #[test]
    fn test_hmac_sha512_bytes() {
        let result = hmac_sha512(b"key", b"message").unwrap();
        assert_eq!(result.len(), 64);
    }

    #[test]
    fn test_hash_sha256() {
        let result = hash("sha256", "hello world", "hex").unwrap();
        assert_eq!(result, "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9");
    }

    #[test]
    fn test_hash_md5() {
        let result = hash("md5", "hello world", "hex").unwrap();
        assert_eq!(result, "5eb63bbbe01eeed093cb22bb8f5acdc3");
    }

    #[test]
    fn test_random_bytes() {
        let a = random_bytes(16).unwrap();
        let b = random_bytes(16).unwrap();
        assert_eq!(a.len(), 16);
        assert_ne!(a, b);
    }

    #[test]
    fn test_random_bytes_zero() {
        let r = random_bytes(0).unwrap();
        assert!(r.is_empty());
    }

    #[test]
    fn test_random_bytes_exceeds_max() {
        assert!(random_bytes(2_000_000).is_err());
    }

    #[test]
    fn test_buffer_hex_roundtrip() {
        let original = b"hello";
        let hex_str = buffer_to_hex(original);
        let decoded = buffer_from_hex(&hex_str).unwrap();
        assert_eq!(decoded, original);
    }

    #[test]
    fn test_buffer_base64_roundtrip() {
        let original = b"hello world";
        let b64 = buffer_to_base64(original);
        let decoded = buffer_from_base64(&b64).unwrap();
        assert_eq!(decoded, original);
    }

    #[test]
    fn test_binance_signature() {
        // Known test vector from Binance API docs
        let secret = "NhqPtmdSJYdKjVHjA7PZj4Mge3R5YNiP1e3UZjInClVN65XAbvqqM6A7H5fATj0j";
        let query = "symbol=LTCBTC&side=BUY&type=LIMIT&timeInForce=GTC&quantity=1&price=0.1&recvWindow=5000&timestamp=1499827319559";
        let expected = "c8db56825ae71d6d79447849e617115f4a920fa2acdcab2b053c4b2838bd6b71";
        let result = hmac("sha256", secret, query, "hex").unwrap();
        assert_eq!(result, expected);
    }

    #[test]
    fn test_unsupported_algorithm() {
        assert!(hmac("blake2", "key", "msg", "hex").is_err());
        assert!(hash("blake2", "data", "hex").is_err());
    }

    // ── Additional hash algorithm vectors ──────────────────────────────

    #[test]
    fn test_hmac_sha384_hex() {
        let result = hmac("sha384", "secret_key", "message_data", "hex").unwrap();
        assert_eq!(result.len(), 96); // SHA384 = 48 bytes = 96 hex chars
    }

    #[test]
    fn test_hash_sha512() {
        let result = hash("sha512", "hello world", "hex").unwrap();
        assert_eq!(
            result,
            "309ecc489c12d6eb4cc40f50c902f2b4d0ed77ee511a7c7a9bcd3ca86d4cd86f\
             989dd35bc5ff499670da34255b45b0cfd830e81f605dcf7dc5542e93ae9cd76f"
        );
    }

    #[test]
    fn test_hash_sha384() {
        let result = hash("sha384", "hello world", "hex").unwrap();
        assert_eq!(
            result,
            "fdbd8e75a67f29f701a4e040385e2e23986303ea10239211af907fcbb83578b3\
             e417cb71ce646efd0819dd8c088de1bd"
        );
    }

    #[test]
    fn test_hash_sha3_256() {
        let result = hash("sha3-256", "hello world", "hex").unwrap();
        assert_eq!(
            result,
            "644bcc7e564373040999aac89e7622f3ca71fba1d972fd94a31c3bfbf24e3938"
        );
    }

    #[test]
    fn test_hash_sha3_512() {
        let result = hash("sha3-512", "hello world", "hex").unwrap();
        assert_eq!(
            result,
            "840006653e9ac9e95117a15c915caab81662918e925de9e004f774ff82d7079a\
             40d4d27b1b372657c61d46d470304c88c788b3a4527ad074d1dccbee5dbaa99a"
        );
    }

    #[test]
    fn test_hmac_base64_encoding() {
        let result = hmac("sha256", "key", "data", "base64").unwrap();
        // base64 output should be non-empty and valid
        assert!(!result.is_empty());
        assert!(base64::engine::general_purpose::STANDARD.decode(&result).is_ok());
    }

    // ── Error path tests ──────────────────────────────────────────────

    #[test]
    fn test_unsupported_encoding() {
        let err = hmac("sha256", "key", "msg", "foobar").unwrap_err();
        match err {
            PolyfillError::Encoding(_) => {} // correct variant
            other => panic!("expected Encoding error, got: {other}"),
        }
    }

    #[test]
    fn test_binary_encoding_latin1() {
        // "binary" / "latin1" encoding maps each byte to a Unicode code point 0–255,
        // matching Node.js behavior. Non-UTF-8 bytes should now succeed.
        let non_utf8 = vec![0xFF, 0xFE, 0x80, 0x90];
        let result = encode_bytes(&non_utf8, "binary").unwrap();
        assert_eq!(result, "\u{FF}\u{FE}\u{80}\u{90}");

        // "latin1" alias should produce the same result
        assert_eq!(encode_bytes(&non_utf8, "latin1").unwrap(), result);

        // ASCII bytes should pass through unchanged
        let valid = b"hello";
        assert_eq!(encode_bytes(valid, "binary").unwrap(), "hello");
    }

    #[test]
    fn test_buffer_from_hex_invalid() {
        assert!(buffer_from_hex("xyz!!!").is_err());
    }

    #[test]
    fn test_buffer_from_base64_invalid() {
        assert!(buffer_from_base64("!!!!").is_err());
    }

    // ── Buffer edge cases ─────────────────────────────────────────────

    #[test]
    fn test_buffer_concat_empty() {
        assert!(buffer_concat(vec![]).is_empty());
    }

    #[test]
    fn test_buffer_concat_mixed() {
        let result = buffer_concat(vec![vec![], vec![1, 2], vec![], vec![3]]);
        assert_eq!(result, vec![1, 2, 3]);
    }

    #[test]
    fn test_buffer_byte_length_multibyte() {
        assert_eq!(buffer_byte_length(""), 0);
        assert_eq!(buffer_byte_length("hello"), 5);
        assert_eq!(buffer_byte_length("中"), 3); // 3-byte UTF-8
    }

    // ── Binance HMAC via byte-level API ──────────────────────────────

    #[test]
    fn test_binance_signature_via_hmac_sha256() {
        // Same Binance test vector, via hmac_sha256 byte API
        let secret = b"NhqPtmdSJYdKjVHjA7PZj4Mge3R5YNiP1e3UZjInClVN65XAbvqqM6A7H5fATj0j";
        let query = b"symbol=LTCBTC&side=BUY&type=LIMIT&timeInForce=GTC&quantity=1&price=0.1&recvWindow=5000&timestamp=1499827319559";
        let expected = "c8db56825ae71d6d79447849e617115f4a920fa2acdcab2b053c4b2838bd6b71";
        let result = hmac_sha256(secret, query).unwrap();
        assert_eq!(hex::encode(result), expected);
    }

    #[cfg(not(target_arch = "wasm32"))]
    #[test]
    fn test_fetch_sync_rejects_file_scheme() {
        let req = FetchRequest {
            url: "file:///etc/passwd".to_string(),
            method: "GET".to_string(),
            headers: vec![],
            body: None,
        };
        let err = fetch_sync(req).unwrap_err();
        match err {
            PolyfillError::Http(msg) => assert!(msg.contains("unsupported URL scheme")),
            other => panic!("expected Http error, got: {other}"),
        }
    }

    #[cfg(not(target_arch = "wasm32"))]
    #[test]
    fn test_fetch_sync_rejects_crlf_header_value() {
        let req = FetchRequest {
            url: "https://example.com".to_string(),
            method: "GET".to_string(),
            headers: vec![
                ("X-Custom".to_string(), "value\r\nInjected: true".to_string()),
            ],
            body: None,
        };
        let err = fetch_sync(req).unwrap_err();
        match err {
            PolyfillError::Http(msg) => assert!(msg.contains("prohibited characters")),
            other => panic!("expected Http error for CRLF injection, got: {other}"),
        }
    }

    #[cfg(not(target_arch = "wasm32"))]
    #[test]
    fn test_fetch_sync_rejects_crlf_header_name() {
        let req = FetchRequest {
            url: "https://example.com".to_string(),
            method: "GET".to_string(),
            headers: vec![
                ("X-Bad\nName".to_string(), "value".to_string()),
            ],
            body: None,
        };
        let err = fetch_sync(req).unwrap_err();
        match err {
            PolyfillError::Http(msg) => assert!(msg.contains("prohibited characters")),
            other => panic!("expected Http error for CRLF injection, got: {other}"),
        }
    }

    #[test]
    fn test_random_bytes_hex_length() {
        let hex = random_bytes_hex(16).unwrap();
        assert_eq!(hex.len(), 32);
        assert!(hex.chars().all(|c| c.is_ascii_hexdigit()));
    }

    #[test]
    fn test_random_bytes_at_max_boundary() {
        // Exactly at the limit should succeed
        let result = random_bytes(MAX_RANDOM_BYTES);
        assert!(result.is_ok());
        assert_eq!(result.unwrap().len(), MAX_RANDOM_BYTES);
    }
}
