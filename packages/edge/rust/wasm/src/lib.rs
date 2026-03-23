use wasm_bindgen::prelude::*;
use octobot_edge_core as core;

/// Compute HMAC — called by JS crypto polyfill
#[wasm_bindgen]
pub fn hmac(
    algorithm: &str,
    secret: &str,
    data: &str,
    encoding: &str,
) -> Result<String, JsValue> {
    core::hmac(algorithm, secret, data, encoding)
        .map_err(|e| JsValue::from_str(&e.to_string()))
}

/// Compute hash — called by JS crypto polyfill
#[wasm_bindgen]
pub fn hash(
    algorithm: &str,
    data: &str,
    encoding: &str,
) -> Result<String, JsValue> {
    core::hash(algorithm, data, encoding)
        .map_err(|e| JsValue::from_str(&e.to_string()))
}

/// HMAC-SHA256 returning raw bytes
#[wasm_bindgen]
pub fn hmac_sha256(key: &[u8], message: &[u8]) -> Result<Vec<u8>, JsValue> {
    core::hmac_sha256(key, message)
        .map_err(|e| JsValue::from_str(&e.to_string()))
}

/// HMAC-SHA256 returning hex string
#[wasm_bindgen]
pub fn hmac_sha256_hex(key: &[u8], message: &[u8]) -> Result<String, JsValue> {
    core::hmac_sha256(key, message)
        .map(hex::encode)
        .map_err(|e| JsValue::from_str(&e.to_string()))
}

/// HMAC-SHA512 returning raw bytes
#[wasm_bindgen]
pub fn hmac_sha512(key: &[u8], message: &[u8]) -> Result<Vec<u8>, JsValue> {
    core::hmac_sha512(key, message)
        .map_err(|e| JsValue::from_str(&e.to_string()))
}

/// HMAC-SHA512 returning hex string
#[wasm_bindgen]
pub fn hmac_sha512_hex(key: &[u8], message: &[u8]) -> Result<String, JsValue> {
    core::hmac_sha512(key, message)
        .map(hex::encode)
        .map_err(|e| JsValue::from_str(&e.to_string()))
}

/// Random bytes as hex string
#[wasm_bindgen]
pub fn random_bytes_hex(size: usize) -> Result<String, JsValue> {
    core::random_bytes_hex(size)
        .map_err(|e| JsValue::from_str(&e.to_string()))
}

/// Random bytes as Uint8Array
#[wasm_bindgen]
pub fn random_bytes(size: usize) -> Result<Vec<u8>, JsValue> {
    core::random_bytes(size)
        .map_err(|e| JsValue::from_str(&e.to_string()))
}

/// Buffer to hex
#[wasm_bindgen]
pub fn buffer_to_hex(data: &[u8]) -> String {
    core::buffer_to_hex(data)
}

/// Buffer from hex
#[wasm_bindgen]
pub fn buffer_from_hex(hex_str: &str) -> Result<Vec<u8>, JsValue> {
    core::buffer_from_hex(hex_str)
        .map_err(|e| JsValue::from_str(&e.to_string()))
}

/// Buffer to base64
#[wasm_bindgen]
pub fn buffer_to_base64(data: &[u8]) -> String {
    core::buffer_to_base64(data)
}

/// Buffer from base64
#[wasm_bindgen]
pub fn buffer_from_base64(b64: &str) -> Result<Vec<u8>, JsValue> {
    core::buffer_from_base64(b64)
        .map_err(|e| JsValue::from_str(&e.to_string()))
}

/// Byte length of UTF-8 string
#[wasm_bindgen]
pub fn buffer_byte_length(s: &str) -> usize {
    core::buffer_byte_length(s)
}

/// Called once on module load — patches globalThis with __rustPolyfills namespace
#[wasm_bindgen(start)]
pub fn install_polyfills() {
    if let Err(e) = install_polyfills_inner() {
        let msg = e.as_string().unwrap_or_else(|| "unknown error installing polyfills".to_string());
        web_sys::console::error_1(&format!("install_polyfills failed: {msg}").into());
    }
}

fn install_polyfills_inner() -> Result<(), JsValue> {
    let global = js_sys::global();
    let rust_obj = js_sys::Object::new();

    // hmac(algorithm, secret, data, encoding) -> string (throws on error)
    js_sys::Reflect::set(&rust_obj, &"hmac".into(),
        &wasm_bindgen::closure::Closure::wrap(
            Box::new(|a: String, s: String, d: String, e: String| {
                match hmac(&a, &s, &d, &e) {
                    Ok(result) => result,
                    Err(err) => {
                        wasm_bindgen::throw_str(&format!("HMAC error: {}", err.as_string().unwrap_or_default()));
                    }
                }
            }) as Box<dyn Fn(String, String, String, String) -> String>
        ).into_js_value()
    )?;

    // hash(algorithm, data, encoding) -> string (throws on error)
    js_sys::Reflect::set(&rust_obj, &"hash".into(),
        &wasm_bindgen::closure::Closure::wrap(
            Box::new(|a: String, d: String, e: String| {
                match hash(&a, &d, &e) {
                    Ok(result) => result,
                    Err(err) => {
                        wasm_bindgen::throw_str(&format!("Hash error: {}", err.as_string().unwrap_or_default()));
                    }
                }
            }) as Box<dyn Fn(String, String, String) -> String>
        ).into_js_value()
    )?;

    // randomBytesHex(size) -> string (throws on error)
    js_sys::Reflect::set(&rust_obj, &"randomBytesHex".into(),
        &wasm_bindgen::closure::Closure::wrap(
            Box::new(|size: usize| {
                match random_bytes_hex(size) {
                    Ok(result) => result,
                    Err(err) => {
                        wasm_bindgen::throw_str(&format!("randomBytesHex error: {}", err.as_string().unwrap_or_default()));
                    }
                }
            }) as Box<dyn Fn(usize) -> String>
        ).into_js_value()
    )?;

    js_sys::Reflect::set(&global, &"__rustPolyfills".into(), &rust_obj)?;
    Ok(())
}
