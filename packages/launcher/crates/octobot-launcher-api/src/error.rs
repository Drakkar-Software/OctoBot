use axum::{
    http::StatusCode,
    response::{IntoResponse, Response},
    Json,
};
use serde_json::json;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum ApiError {
    #[error("not found: {0}")]
    NotFound(String),
    #[error("unauthorized")]
    Unauthorized,
    #[error("forbidden")]
    Forbidden,
    #[error("too many requests")]
    TooManyRequests,
    #[error("bad request: {0}")]
    BadRequest(String),
    #[error("internal error: {0}")]
    Internal(String),
    #[error("conflict: {0}")]
    Conflict(String),
    #[error("service unavailable: {0}")]
    ServiceUnavailable(String),
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let (status, type_uri, title, detail) = match &self {
            ApiError::NotFound(d) => (
                StatusCode::NOT_FOUND,
                "https://octobot.software/errors/not-found",
                "Not Found",
                d.clone(),
            ),
            ApiError::Unauthorized => (
                StatusCode::UNAUTHORIZED,
                "https://octobot.software/errors/unauthorized",
                "Unauthorized",
                "Authentication required or invalid credentials".to_string(),
            ),
            ApiError::Forbidden => (
                StatusCode::FORBIDDEN,
                "https://octobot.software/errors/forbidden",
                "Forbidden",
                "Insufficient scope for this operation".to_string(),
            ),
            ApiError::TooManyRequests => (
                StatusCode::TOO_MANY_REQUESTS,
                "https://octobot.software/errors/too-many-requests",
                "Too Many Requests",
                "Too many failed authentication attempts".to_string(),
            ),
            ApiError::BadRequest(d) => (
                StatusCode::BAD_REQUEST,
                "https://octobot.software/errors/bad-request",
                "Bad Request",
                d.clone(),
            ),
            ApiError::Internal(d) => (
                StatusCode::INTERNAL_SERVER_ERROR,
                "https://octobot.software/errors/internal",
                "Internal Server Error",
                d.clone(),
            ),
            ApiError::Conflict(d) => (
                StatusCode::CONFLICT,
                "https://octobot.software/errors/conflict",
                "Conflict",
                d.clone(),
            ),
            ApiError::ServiceUnavailable(d) => (
                StatusCode::SERVICE_UNAVAILABLE,
                "https://octobot.software/errors/service-unavailable",
                "Service Unavailable",
                d.clone(),
            ),
        };

        let body = json!({
            "type": type_uri,
            "title": title,
            "status": status.as_u16(),
            "detail": detail,
        });

        let mut response = (status, Json(body)).into_response();
        response.headers_mut().insert(
            axum::http::header::CONTENT_TYPE,
            axum::http::HeaderValue::from_static("application/problem+json"),
        );
        response
    }
}
