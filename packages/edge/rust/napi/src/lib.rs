use napi_derive::napi;
use octobot_edge_core as core;

#[napi]
pub fn hmac_sha256(key: Vec<u8>, message: Vec<u8>) -> napi::Result<Vec<u8>> {
    core::hmac_sha256(&key, &message)
        .map_err(|e| napi::Error::from_reason(e.to_string()))
}

#[napi]
pub fn hmac_sha256_hex(key: Vec<u8>, message: Vec<u8>) -> napi::Result<String> {
    core::hmac_sha256(&key, &message)
        .map(hex::encode)
        .map_err(|e| napi::Error::from_reason(e.to_string()))
}

#[napi]
pub fn hmac_sha512(key: Vec<u8>, message: Vec<u8>) -> napi::Result<Vec<u8>> {
    core::hmac_sha512(&key, &message)
        .map_err(|e| napi::Error::from_reason(e.to_string()))
}

#[napi]
pub fn hmac_sha512_hex(key: Vec<u8>, message: Vec<u8>) -> napi::Result<String> {
    core::hmac_sha512(&key, &message)
        .map(hex::encode)
        .map_err(|e| napi::Error::from_reason(e.to_string()))
}

#[napi]
pub fn hmac(algorithm: String, secret: String, data: String, encoding: String) -> napi::Result<String> {
    core::hmac(&algorithm, &secret, &data, &encoding)
        .map_err(|e| napi::Error::from_reason(e.to_string()))
}

#[napi]
pub fn hash(algorithm: String, data: String, encoding: String) -> napi::Result<String> {
    core::hash(&algorithm, &data, &encoding)
        .map_err(|e| napi::Error::from_reason(e.to_string()))
}

#[napi]
pub fn random_bytes_hex(size: u32) -> napi::Result<String> {
    core::random_bytes_hex(size as usize)
        .map_err(|e| napi::Error::from_reason(e.to_string()))
}

#[napi]
pub fn random_bytes(size: u32) -> napi::Result<Vec<u8>> {
    core::random_bytes(size as usize)
        .map_err(|e| napi::Error::from_reason(e.to_string()))
}

// ── Buffer operations ────────────────────────────────────────────────────────

#[napi]
pub fn buffer_to_hex(data: Vec<u8>) -> String {
    core::buffer_to_hex(&data)
}

#[napi]
pub fn buffer_from_hex(hex_str: String) -> napi::Result<Vec<u8>> {
    core::buffer_from_hex(&hex_str)
        .map_err(|e| napi::Error::from_reason(e.to_string()))
}

#[napi]
pub fn buffer_to_base64(data: Vec<u8>) -> String {
    core::buffer_to_base64(&data)
}

#[napi]
pub fn buffer_from_base64(b64: String) -> napi::Result<Vec<u8>> {
    core::buffer_from_base64(&b64)
        .map_err(|e| napi::Error::from_reason(e.to_string()))
}

#[napi]
pub fn buffer_byte_length(utf8_str: String) -> u32 {
    core::buffer_byte_length(&utf8_str).min(u32::MAX as usize) as u32
}
