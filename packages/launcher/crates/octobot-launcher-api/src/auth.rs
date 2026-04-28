use std::sync::Arc;

use axum::{
    body::Body,
    extract::Request,
    middleware::Next,
    response::Response,
};

use crate::{
    error::ApiError,
    lockout::Lockout,
    token_store::{TOKEN_PREFIX, TokenRecord, TokenStore, token_has_scope},
};

#[derive(Debug, Clone)]
pub struct LocalSocketMarker;

#[derive(Debug, Clone)]
pub struct AuthLayer {
    pub token_store: Arc<TokenStore>,
    pub lockout: Arc<Lockout>,
    pub required_scope: Option<String>,
}

impl AuthLayer {
    pub fn new(
        token_store: Arc<TokenStore>,
        lockout: Arc<Lockout>,
        required_scope: Option<&str>,
    ) -> Self {
        Self {
            token_store,
            lockout,
            required_scope: required_scope.map(str::to_string),
        }
    }
}

pub async fn auth_middleware(
    axum::extract::State(layer): axum::extract::State<AuthLayer>,
    mut request: Request<Body>,
    next: Next,
) -> Result<Response, ApiError> {
    if request.extensions().get::<LocalSocketMarker>().is_some() {
        return Ok(next.run(request).await);
    }

    let source_ip = extract_source_ip(&request);

    let auth_header = request
        .headers()
        .get(axum::http::header::AUTHORIZATION)
        .and_then(|v| v.to_str().ok())
        .map(str::to_string);

    let raw_token = match auth_header {
        Some(ref h) if h.starts_with("Bearer ") => h[7..].to_string(),
        _ => return Err(ApiError::Unauthorized),
    };

    if !raw_token.starts_with(TOKEN_PREFIX) {
        return Err(ApiError::Unauthorized);
    }

    if !layer.lockout.check(&source_ip) {
        return Err(ApiError::TooManyRequests);
    }

    layer.token_store.reload();
    let record = layer.token_store.verify(&raw_token);
    let Some(record) = record else {
        layer.lockout.record_failure(&source_ip);
        return Err(ApiError::Unauthorized);
    };

    layer.lockout.record_success(&source_ip);

    if let Some(ref scope) = layer.required_scope {
        if !token_has_scope(&record, scope) {
            return Err(ApiError::Forbidden);
        }
    }

    let token_id = record.id.clone();
    tracing::debug!(token_id = %token_id, "authenticated request");

    {
        let store = Arc::clone(&layer.token_store);
        let id = token_id.clone();
        tokio::spawn(async move {
            store.update_last_used(&id);
        });
    }

    request.extensions_mut().insert(record);
    Ok(next.run(request).await)
}

fn extract_source_ip(request: &Request<Body>) -> String {
    request
        .headers()
        .get("x-forwarded-for")
        .and_then(|v| v.to_str().ok())
        .and_then(|s| s.split(',').next())
        .map(|s| s.trim().to_string())
        .or_else(|| {
            request
                .extensions()
                .get::<axum::extract::ConnectInfo<std::net::SocketAddr>>()
                .map(|ci| ci.0.ip().to_string())
        })
        .unwrap_or_else(|| "unknown".to_string())
}

pub fn extract_token_record(request: &Request<Body>) -> Option<&TokenRecord> {
    request.extensions().get::<TokenRecord>()
}
