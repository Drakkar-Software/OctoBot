use axum::{Json, response::IntoResponse};
use serde_json::json;

pub async fn check_updates() -> impl IntoResponse {
    Json(json!({
        "status": "ok",
        "updates_available": false,
    }))
}

pub async fn update_launcher() -> impl IntoResponse {
    Json(json!({ "status": "accepted" }))
}
