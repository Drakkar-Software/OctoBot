// UniFFI wrapper for iOS/Android (React Native Turbo Module).
// uniffi-bindgen-react-native reads these annotations and generates:
//   - TypeScript types + JSI C++ glue
//   - Swift Turbo Module (iOS)
//   - Kotlin Turbo Module (Android)

uniffi::setup_scaffolding!();

use octobot_edge_core as core;

// ── Error type (re-exported for UniFFI) ──────────────────────────────────────

#[derive(Debug, thiserror::Error, uniffi::Error)]
pub enum EdgePolyfillError {
    #[error("Unsupported algorithm: {0}")]
    UnsupportedAlgorithm(String),
    #[error("HTTP error: {0}")]
    Http(String),
    #[error("Encoding error: {0}")]
    Encoding(String),
}

impl From<core::PolyfillError> for EdgePolyfillError {
    fn from(e: core::PolyfillError) -> Self {
        match e {
            core::PolyfillError::UnsupportedAlgorithm(s) => Self::UnsupportedAlgorithm(s),
            core::PolyfillError::Http(s) => Self::Http(s),
            core::PolyfillError::Encoding(s) => Self::Encoding(s),
        }
    }
}

// ── Fetch types (exposed to TypeScript) ──────────────────────────────────────

#[derive(uniffi::Record)]
pub struct FetchRequest {
    pub url: String,
    pub method: String,
    pub headers: Vec<HeaderEntry>,
    pub body: Option<String>,
}

#[derive(uniffi::Record)]
pub struct FetchResponse {
    pub status: u16,
    pub ok: bool,
    pub body: String,
    pub headers: Vec<HeaderEntry>,
}

#[derive(uniffi::Record)]
pub struct HeaderEntry {
    pub name: String,
    pub value: String,
}

// ── HMAC ─────────────────────────────────────────────────────────────────────

/// Compute HMAC. algorithm: "sha256"|"sha512"|"sha384"
/// encoding: "hex"|"base64"
#[uniffi::export]
pub fn hmac(
    algorithm: String,
    secret: String,
    data: String,
    encoding: String,
) -> Result<String, EdgePolyfillError> {
    core::hmac(&algorithm, &secret, &data, &encoding).map_err(Into::into)
}

// ── Hash ─────────────────────────────────────────────────────────────────────

/// Compute hash. algorithm: "sha256"|"sha512"|"sha384"|"md5"|"sha3-256"|"sha3-512"
#[uniffi::export]
pub fn hash(
    algorithm: String,
    data: String,
    encoding: String,
) -> Result<String, EdgePolyfillError> {
    core::hash(&algorithm, &data, &encoding).map_err(Into::into)
}

// ── Random bytes ─────────────────────────────────────────────────────────────

#[uniffi::export]
pub fn random_bytes_hex(size: u32) -> Result<String, EdgePolyfillError> {
    core::random_bytes_hex(size as usize).map_err(Into::into)
}

#[uniffi::export]
pub fn random_bytes(size: u32) -> Result<Vec<u8>, EdgePolyfillError> {
    core::random_bytes(size as usize).map_err(Into::into)
}

// ── Buffer ops ───────────────────────────────────────────────────────────────

#[uniffi::export]
pub fn buffer_to_hex(data: Vec<u8>) -> String {
    core::buffer_to_hex(&data)
}

#[uniffi::export]
pub fn buffer_from_hex(hex_str: String) -> Result<Vec<u8>, EdgePolyfillError> {
    core::buffer_from_hex(&hex_str).map_err(Into::into)
}

#[uniffi::export]
pub fn buffer_to_base64(data: Vec<u8>) -> String {
    core::buffer_to_base64(&data)
}

#[uniffi::export]
pub fn buffer_from_base64(b64: String) -> Result<Vec<u8>, EdgePolyfillError> {
    core::buffer_from_base64(&b64).map_err(Into::into)
}

#[uniffi::export]
pub fn buffer_byte_length(utf8_str: String) -> u32 {
    core::buffer_byte_length(&utf8_str).min(u32::MAX as usize) as u32
}

// ── Fetch (async via tokio, mapped to JS Promise by uniffi-bindgen-RN) ───────

/// Performs HTTP request from Rust using reqwest + rustls.
/// Mapped to a TypeScript Promise<FetchResponse> automatically.
#[uniffi::export]
pub async fn fetch(req: FetchRequest) -> Result<FetchResponse, EdgePolyfillError> {
    let core_req = core::FetchRequest {
        url: req.url,
        method: req.method,
        headers: req.headers.into_iter().map(|h| (h.name, h.value)).collect(),
        body: req.body,
    };

    let result = tokio::task::spawn_blocking(move || {
        core::fetch_sync(core_req)
    })
    .await
    .map_err(|e| EdgePolyfillError::Http(e.to_string()))?
    .map_err(EdgePolyfillError::from)?;

    Ok(FetchResponse {
        status: result.status,
        ok: result.ok,
        body: result.body,
        headers: result.headers
            .into_iter()
            .map(|(name, value)| HeaderEntry { name, value })
            .collect(),
    })
}
