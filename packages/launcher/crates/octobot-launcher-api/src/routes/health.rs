use axum::{Json, response::IntoResponse};
use serde_json::json;

pub async fn health() -> impl IntoResponse {
    Json(json!({ "status": "ok" }))
}

pub async fn version() -> impl IntoResponse {
    Json(json!({ "version": env!("CARGO_PKG_VERSION") }))
}
