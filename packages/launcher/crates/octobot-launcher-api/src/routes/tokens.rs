use std::sync::Arc;

use axum::{
    Json,
    extract::{Path, State},
    response::IntoResponse,
};
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};


use crate::error::ApiError;
use crate::token_store::{TokenRecord, TokenStore, default_scopes};

#[derive(Debug, Deserialize)]
pub struct CreateTokenBody {
    pub label: String,
    pub scopes: Option<Vec<String>>,
    pub expires_at: Option<DateTime<Utc>>,
}

#[derive(Debug, Serialize)]
pub struct TokenResponse {
    pub id: String,
    pub label: String,
    pub scopes: Vec<String>,
    pub created_at: DateTime<Utc>,
    pub last_used_at: Option<DateTime<Utc>>,
    pub expires_at: Option<DateTime<Utc>>,
    pub revoked: bool,
}

impl From<TokenRecord> for TokenResponse {
    fn from(r: TokenRecord) -> Self {
        Self {
            id: r.id,
            label: r.label,
            scopes: r.scopes,
            created_at: r.created_at,
            last_used_at: r.last_used_at,
            expires_at: r.expires_at,
            revoked: r.revoked,
        }
    }
}

#[derive(Debug, Serialize)]
pub struct CreateTokenResponse {
    pub token: TokenResponse,
    pub raw_token: String,
}

pub async fn list_tokens(
    State(token_store): State<Arc<TokenStore>>,
) -> impl IntoResponse {
    let records = token_store.list();
    let responses: Vec<TokenResponse> = records.into_iter().map(TokenResponse::from).collect();
    Json(responses)
}

pub async fn create_token(
    State(token_store): State<Arc<TokenStore>>,
    Json(body): Json<CreateTokenBody>,
) -> Result<impl IntoResponse, ApiError> {
    let scopes = body.scopes.unwrap_or_else(default_scopes);
    let (record, raw_token) = token_store
        .create(body.label, scopes, body.expires_at)
        .map_err(|e| ApiError::Internal(e.to_string()))?;

    let response = CreateTokenResponse {
        token: TokenResponse::from(record),
        raw_token,
    };

    Ok((axum::http::StatusCode::CREATED, Json(response)))
}

pub async fn revoke_token(
    State(token_store): State<Arc<TokenStore>>,
    Path(id): Path<String>,
) -> Result<impl IntoResponse, ApiError> {
    match token_store
        .revoke(&id)
        .map_err(|e| ApiError::Internal(e.to_string()))?
    {
        true => Ok(axum::http::StatusCode::NO_CONTENT),
        false => Err(ApiError::NotFound(format!("token '{id}' not found"))),
    }
}
