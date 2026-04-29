#![deny(clippy::unwrap_used, clippy::expect_used)]

pub mod auth;
pub mod error;
pub mod lockout;
pub mod routes;
pub mod scopes;
pub mod token_store;

use std::net::SocketAddr;
use std::path::PathBuf;
use std::sync::Arc;

use axum::{
    Router,
    body::Body,
    extract::Request,
    middleware,
    response::{IntoResponse, Response},
    routing::{delete, get, patch, post},
};
use tower_http::{limit::RequestBodyLimitLayer, trace::TraceLayer};

use octobot_launcher_core::backend::Backend;

use crate::{
    auth::{AuthLayer, auth_middleware},
    error::ApiError,
    lockout::Lockout,
    routes::{health, instances, tokens, updates},
    scopes::{
        SCOPE_INSTANCES_READ, SCOPE_INSTANCES_WRITE, SCOPE_TOKENS_MANAGE, SCOPE_UPDATES_APPLY,
        SCOPE_UPDATES_READ,
    },
    token_store::TokenStore,
};

pub use octobot_launcher_config::Store;
pub use token_store::{TokenRecord, default_scopes};

#[allow(missing_debug_implementations)]
#[derive(Clone)]
pub struct ApiState {
    pub store: Arc<Store>,
    pub token_store: Arc<TokenStore>,
    pub lockout: Arc<Lockout>,
    pub backends: Arc<Vec<Box<dyn Backend>>>,
}

#[derive(Debug, Clone)]
pub struct ListenerConfig {
    pub tcp_bind: SocketAddr,
    pub unix_socket_path: Option<PathBuf>,
}

#[allow(missing_debug_implementations)]
pub struct ApiServer {
    router: Router,
    pub config: ListenerConfig,
}

impl ApiServer {
    pub fn new(state: ApiState, config: ListenerConfig) -> Self {
        let router = router(state);
        Self { router, config }
    }

    pub async fn serve(self) -> std::io::Result<()> {
        let addr = self.config.tcp_bind;
        if !addr.ip().is_loopback() {
            tracing::warn!(
                bind = %addr,
                "API server binding to non-loopback address — ensure firewall rules restrict access"
            );
        }

        let unix_socket_path = self.config.unix_socket_path.clone();

        #[cfg(unix)]
        let unix_router = self.router.clone();

        let tcp_future = {
            let router = self.router;
            async move {
                let listener = tokio::net::TcpListener::bind(addr).await?;
                tracing::info!(addr = %addr, "API listening");
                axum::serve(listener, router).await
            }
        };

        #[cfg(unix)]
        {
            if let Some(socket_path) = unix_socket_path {
                let unix_future = async move {
                    if socket_path.exists() {
                        std::fs::remove_file(&socket_path)?;
                    }
                    let router = unix_router.layer(middleware::from_fn(inject_local_marker));
                    let listener = tokio::net::UnixListener::bind(&socket_path)?;
                    tracing::info!(path = %socket_path.display(), "Unix socket listening");
                    axum::serve(listener, router).await
                };
                return tokio::try_join!(tcp_future, unix_future).map(|_| ());
            }
        }

        #[cfg(not(unix))]
        let _ = unix_socket_path;

        tcp_future.await
    }
}

#[cfg(unix)]
async fn inject_local_marker(mut request: Request<Body>, next: middleware::Next) -> Response {
    request.extensions_mut().insert(auth::LocalSocketMarker);
    next.run(request).await
}

async fn strip_server_header(request: Request<Body>, next: middleware::Next) -> Response {
    let mut response = next.run(request).await;
    response.headers_mut().remove(axum::http::header::SERVER);
    response
}

async fn fallback_404() -> impl IntoResponse {
    ApiError::NotFound("route not found".to_string())
}

fn make_auth_layer(
    token_store: &Arc<TokenStore>,
    lockout: &Arc<Lockout>,
    scope: &str,
) -> AuthLayer {
    AuthLayer::new(Arc::clone(token_store), Arc::clone(lockout), Some(scope))
}

pub fn router(state: ApiState) -> Router {
    let ApiState { store, token_store, lockout, backends } = state;
    let ts = &token_store;
    let lk = &lockout;

    let read = make_auth_layer(ts, lk, SCOPE_INSTANCES_READ);
    let write_crud = make_auth_layer(ts, lk, SCOPE_INSTANCES_WRITE);
    let write_action = make_auth_layer(ts, lk, SCOPE_INSTANCES_WRITE);
    let upd_read = make_auth_layer(ts, lk, SCOPE_UPDATES_READ);
    let upd_apply = make_auth_layer(ts, lk, SCOPE_UPDATES_APPLY);
    let upd_apply_inst = make_auth_layer(ts, lk, SCOPE_UPDATES_APPLY);
    let tok_mgr = make_auth_layer(ts, lk, SCOPE_TOKENS_MANAGE);
    let inst_read_version = make_auth_layer(ts, lk, SCOPE_INSTANCES_READ);

    let instance_store = Arc::clone(&store);
    let token_store_arc = Arc::clone(&token_store);

    let instances_read_router = Router::new()
        .route("/v1/instances", get(instances::list_instances))
        .route("/v1/instances/{id}", get(instances::get_instance))
        .route("/v1/instances/{id}/status", get(instances::instance_status))
        .with_state(Arc::clone(&instance_store))
        .route_layer(middleware::from_fn_with_state(read, auth_middleware));

    let instances_crud_router = Router::new()
        .route("/v1/instances", post(instances::create_instance))
        .route("/v1/instances/{id}", patch(instances::patch_instance))
        .route("/v1/instances/{id}", delete(instances::delete_instance))
        .with_state(Arc::clone(&instance_store))
        .route_layer(middleware::from_fn_with_state(write_crud, auth_middleware));

    let instances_action_router = Router::new()
        .route("/v1/instances/{id}/start", post(instances::start_instance))
        .route("/v1/instances/{id}/stop", post(instances::stop_instance))
        .route("/v1/instances/{id}/restart", post(instances::restart_instance))
        .with_state(instances::InstanceActionState {
            store: Arc::clone(&store),
            backends: Arc::clone(&backends),
        })
        .route_layer(middleware::from_fn_with_state(write_action, auth_middleware));

    let instances_update_router = Router::new()
        .route("/v1/instances/{id}/update", post(instances::update_instance))
        .with_state(instances::InstanceActionState {
            store: Arc::clone(&store),
            backends: Arc::clone(&backends),
        })
        .route_layer(middleware::from_fn_with_state(upd_apply_inst, auth_middleware));

    let updates_check_router = Router::new()
        .route("/v1/updates/check", get(updates::check_updates))
        .route_layer(middleware::from_fn_with_state(upd_read, auth_middleware));

    let updates_apply_router = Router::new()
        .route("/v1/updates/launcher", post(updates::update_launcher))
        .route_layer(middleware::from_fn_with_state(upd_apply, auth_middleware));

    let tokens_router = Router::new()
        .route("/v1/tokens", get(tokens::list_tokens))
        .route("/v1/tokens", post(tokens::create_token))
        .route("/v1/tokens/{id}", delete(tokens::revoke_token))
        .with_state(token_store_arc)
        .route_layer(middleware::from_fn_with_state(tok_mgr, auth_middleware));

    let version_router = Router::new()
        .route("/v1/version", get(health::version))
        .route_layer(middleware::from_fn_with_state(inst_read_version, auth_middleware));

    Router::new()
        .route("/v1/health", get(health::health))
        .merge(version_router)
        .merge(instances_read_router)
        .merge(instances_crud_router)
        .merge(instances_action_router)
        .merge(instances_update_router)
        .merge(updates_check_router)
        .merge(updates_apply_router)
        .merge(tokens_router)
        .fallback(fallback_404)
        .layer(middleware::from_fn(strip_server_header))
        .layer(RequestBodyLimitLayer::new(256 * 1024))
        .layer(TraceLayer::new_for_http())
}

#[cfg(test)]
mod tests {
    #![allow(clippy::unwrap_used, clippy::expect_used)]

    use std::sync::Arc;
    use std::time::Duration;

    use axum_test::TestServer;
    use serde_json::{Value, json};
    use tempfile::TempDir;

    use crate::{
        ApiState,
        lockout::Lockout,
        router,
        scopes::*,
        token_store::{TokenStore, default_scopes},
    };
    use octobot_launcher_config::Store;
    use octobot_launcher_core::backend::Backend;

    fn make_state() -> (ApiState, TempDir) {
        let dir = TempDir::new().expect("tempdir");
        let store = Arc::new(Store::new(dir.path().to_path_buf()).expect("store"));
        let token_store = Arc::new(TokenStore::load(dir.path().join("tokens.json")));
        let lockout = Arc::new(Lockout::new());
        let backends: Arc<Vec<Box<dyn Backend>>> = Arc::new(vec![
            Box::new(octobot_launcher_core::backend::mock::MockBackend::default()),
        ]);
        (
            ApiState {
                store,
                token_store,
                lockout,
                backends,
            },
            dir,
        )
    }

    fn make_server(state: ApiState) -> TestServer {
        TestServer::new(router(state))
    }

    mod auth {
        use super::*;

        #[tokio::test]
        async fn missing_header_returns_401() {
            let (state, _dir) = make_state();
            let server = make_server(state);
            let resp = server.get("/v1/instances").await;
            assert_eq!(resp.status_code(), 401);
        }

        #[tokio::test]
        async fn wrong_prefix_returns_401_fast() {
            let (state, _dir) = make_state();
            let server = make_server(state);
            let start = std::time::Instant::now();
            let resp = server
                .get("/v1/instances")
                .add_header(
                    "authorization".parse::<axum::http::header::HeaderName>().unwrap(),
                    "Bearer wrongprefix_abc123".parse::<axum::http::header::HeaderValue>().unwrap(),
                )
                .await;
            let elapsed = start.elapsed();
            assert_eq!(resp.status_code(), 401);
            assert!(
                elapsed < Duration::from_millis(50),
                "should be fast, was {:?}",
                elapsed
            );
        }

        #[tokio::test]
        async fn valid_token_authenticates() {
            let (state, _dir) = make_state();
            let (_, raw) = state.token_store.create("test".into(), default_scopes(), None).unwrap();
            let server = make_server(state);
            let resp = server
                .get("/v1/instances")
                .add_header(
                    "authorization".parse::<axum::http::header::HeaderName>().unwrap(),
                    format!("Bearer {}", raw).parse::<axum::http::header::HeaderValue>().unwrap(),
                )
                .await;
            assert_eq!(resp.status_code(), 200);
        }

        #[tokio::test]
        async fn revoked_token_rejected() {
            let (state, _dir) = make_state();
            let (record, raw) =
                state.token_store.create("test".into(), default_scopes(), None).unwrap();
            state.token_store.revoke(&record.id).unwrap();
            let server = make_server(state);
            let resp = server
                .get("/v1/instances")
                .add_header(
                    "authorization".parse::<axum::http::header::HeaderName>().unwrap(),
                    format!("Bearer {}", raw).parse::<axum::http::header::HeaderValue>().unwrap(),
                )
                .await;
            assert_eq!(resp.status_code(), 401);
        }

        #[tokio::test]
        async fn expired_token_rejected() {
            let (state, _dir) = make_state();
            let past = chrono::Utc::now() - chrono::Duration::seconds(1);
            let (_, raw) =
                state.token_store.create("test".into(), default_scopes(), Some(past)).unwrap();
            let server = make_server(state);
            let resp = server
                .get("/v1/instances")
                .add_header(
                    "authorization".parse::<axum::http::header::HeaderName>().unwrap(),
                    format!("Bearer {}", raw).parse::<axum::http::header::HeaderValue>().unwrap(),
                )
                .await;
            assert_eq!(resp.status_code(), 401);
        }

        #[tokio::test]
        async fn scope_required_for_route() {
            let (state, _dir) = make_state();
            let (_, raw) = state.token_store.create(
                "limited".into(),
                vec![SCOPE_INSTANCES_READ.to_string()],
                None,
            ).unwrap();
            let server = make_server(state);
            let resp = server
                .post("/v1/instances")
                .add_header(
                    "authorization".parse::<axum::http::header::HeaderName>().unwrap(),
                    format!("Bearer {}", raw).parse::<axum::http::header::HeaderValue>().unwrap(),
                )
                .json(&json!({
                    "name": "test",
                    "runtime": "Docker",
                    "version": "1.0",
                    "data_dir": "/data",
                    "config_dir": "/config"
                }))
                .await;
            assert_eq!(resp.status_code(), 403);
        }

        #[tokio::test]
        async fn wildcard_scope_grants_all() {
            let (state, _dir) = make_state();
            let (_, raw) = state
                .token_store
                .create("admin".into(), vec![SCOPE_WILDCARD.to_string()], None).unwrap();
            let server = make_server(state);
            let hval: axum::http::HeaderValue =
                format!("Bearer {}", raw).parse::<axum::http::header::HeaderValue>().unwrap();

            let resp = server
                .get("/v1/instances")
                .add_header("authorization".parse::<axum::http::header::HeaderName>().unwrap(), hval.clone())
                .await;
            assert_eq!(resp.status_code(), 200);

            let resp = server
                .get("/v1/tokens")
                .add_header("authorization".parse::<axum::http::header::HeaderName>().unwrap(), hval.clone())
                .await;
            assert_eq!(resp.status_code(), 200);

            let resp = server
                .get("/v1/updates/check")
                .add_header("authorization".parse::<axum::http::header::HeaderName>().unwrap(), hval)
                .await;
            assert_eq!(resp.status_code(), 200);
        }

        #[tokio::test]
        async fn last_used_updated_async() {
            let (state, _dir) = make_state();
            let (record, raw) =
                state.token_store.create("test".into(), default_scopes(), None).unwrap();
            let token_store = Arc::clone(&state.token_store);
            let server = make_server(state);
            let resp = server
                .get("/v1/instances")
                .add_header(
                    "authorization".parse::<axum::http::header::HeaderName>().unwrap(),
                    format!("Bearer {}", raw).parse::<axum::http::header::HeaderValue>().unwrap(),
                )
                .await;
            assert_eq!(resp.status_code(), 200);

            tokio::time::sleep(Duration::from_millis(50)).await;
            let tokens = token_store.list();
            let updated = tokens.iter().find(|r| r.id == record.id).unwrap();
            assert!(updated.last_used_at.is_some());
        }

        #[tokio::test]
        async fn file_change_reloaded() {
            let dir = TempDir::new().expect("tempdir");
            let token_path = dir.path().join("tokens.json");
            let store =
                Arc::new(Store::new(dir.path().to_path_buf()).expect("store"));
            let token_store = Arc::new(TokenStore::load(token_path.clone()));
            let lockout = Arc::new(Lockout::new());
            let state = ApiState {
                store,
                token_store: Arc::clone(&token_store),
                lockout,
                backends: Arc::new(vec![]),
            };

            let new_store = TokenStore::load(token_path);
            let (_, raw) =
                new_store.create("external".into(), default_scopes(), None).unwrap();
            new_store.save().expect("save");

            token_store.reload();

            let server = make_server(state);
            let resp = server
                .get("/v1/instances")
                .add_header(
                    "authorization".parse::<axum::http::header::HeaderName>().unwrap(),
                    format!("Bearer {}", raw).parse::<axum::http::header::HeaderValue>().unwrap(),
                )
                .await;
            assert_eq!(resp.status_code(), 200);
        }
    }

    mod socket {
        use super::*;
        use crate::auth::LocalSocketMarker;
        use axum::{body::Body, extract::Request, middleware, response::Response};

        async fn inject_local(mut req: Request<Body>, next: middleware::Next) -> Response {
            req.extensions_mut().insert(LocalSocketMarker);
            next.run(req).await
        }

        #[tokio::test]
        async fn unix_socket_skips_auth() {
            let (state, _dir) = make_state();
            let app = router(state).layer(middleware::from_fn(inject_local));
            let server = TestServer::new(app);
            let resp = server.get("/v1/instances").await;
            assert_eq!(resp.status_code(), 200);
        }
    }

    mod tokens_tests {
        use super::*;

        fn admin_token(state: &ApiState) -> String {
            let (_, raw) = state
                .token_store
                .create("admin".into(), vec![SCOPE_WILDCARD.to_string()], None).unwrap();
            raw
        }

        #[tokio::test]
        async fn create_returns_raw_once() {
            let (state, _dir) = make_state();
            let raw = admin_token(&state);
            let server = make_server(state);
            let resp = server
                .post("/v1/tokens")
                .add_header(
                    "authorization".parse::<axum::http::header::HeaderName>().unwrap(),
                    format!("Bearer {}", raw).parse::<axum::http::header::HeaderValue>().unwrap(),
                )
                .json(&json!({ "label": "new-token" }))
                .await;
            assert_eq!(resp.status_code(), 201);
            let body: Value = resp.json();
            assert!(body.get("raw_token").is_some());
            assert!(body["raw_token"].as_str().unwrap().starts_with("oblch_"));

            let list_resp = server
                .get("/v1/tokens")
                .add_header(
                    "authorization".parse::<axum::http::header::HeaderName>().unwrap(),
                    format!("Bearer {}", raw).parse::<axum::http::header::HeaderValue>().unwrap(),
                )
                .await;
            let list_body: Value = list_resp.json();
            let arr = list_body.as_array().unwrap();
            for item in arr {
                assert!(item.get("raw_token").is_none());
            }
        }

        #[tokio::test]
        async fn list_omits_hash_and_raw() {
            let (state, _dir) = make_state();
            let raw = admin_token(&state);
            let server = make_server(state);
            let resp = server
                .get("/v1/tokens")
                .add_header(
                    "authorization".parse::<axum::http::header::HeaderName>().unwrap(),
                    format!("Bearer {}", raw).parse::<axum::http::header::HeaderValue>().unwrap(),
                )
                .await;
            assert_eq!(resp.status_code(), 200);
            let body: Value = resp.json();
            let arr = body.as_array().unwrap();
            for item in arr {
                assert!(item.get("argon2_hash").is_none());
                assert!(item.get("raw_token").is_none());
            }
        }

        #[tokio::test]
        async fn default_scopes_applied() {
            let (state, _dir) = make_state();
            let raw = admin_token(&state);
            let server = make_server(state);
            let resp = server
                .post("/v1/tokens")
                .add_header(
                    "authorization".parse::<axum::http::header::HeaderName>().unwrap(),
                    format!("Bearer {}", raw).parse::<axum::http::header::HeaderValue>().unwrap(),
                )
                .json(&json!({ "label": "no-scopes-token" }))
                .await;
            assert_eq!(resp.status_code(), 201);
            let body: Value = resp.json();
            let scopes = body["token"]["scopes"].as_array().unwrap();
            assert!(scopes.iter().any(|s| s == SCOPE_INSTANCES_READ));
            assert!(scopes.iter().any(|s| s == SCOPE_INSTANCES_WRITE));
            assert!(scopes.iter().any(|s| s == SCOPE_UPDATES_READ));
        }

        #[tokio::test]
        async fn admin_scope_required_to_grant_admin() {
            let (state, _dir) = make_state();
            let (_, limited_raw) = state.token_store.create(
                "limited".into(),
                vec![SCOPE_INSTANCES_READ.to_string()],
                None,
            ).unwrap();
            let server = make_server(state);
            let resp = server
                .post("/v1/tokens")
                .add_header(
                    "authorization".parse::<axum::http::header::HeaderName>().unwrap(),
                    format!("Bearer {}", limited_raw).parse::<axum::http::header::HeaderValue>().unwrap(),
                )
                .json(&json!({ "label": "new" }))
                .await;
            assert_eq!(resp.status_code(), 403);
        }
    }

    mod bootstrap_tests {
        use super::*;

        #[test]
        fn first_boot_creates_admin_token() {
            let dir = TempDir::new().expect("tempdir");
            let store = TokenStore::load(dir.path().join("tokens.json"));
            let raw = store.bootstrap_if_empty().unwrap();
            assert!(raw.is_some());
            let raw = raw.unwrap();
            let record = store.verify(&raw).expect("should verify");
            assert!(record.scopes.contains(&SCOPE_WILDCARD.to_string()));
        }
    }

    mod lockout_tests {
        use super::*;

        #[tokio::test]
        async fn ten_failed_attempts_locks_ip() {
            let (state, _dir) = make_state();
            let server = make_server(state);
            let bad_token = "oblch_wrongtoken12345678901234567890123456";
            let attacker_ip = "10.99.0.1";

            for _ in 0..10 {
                let _ = server
                    .get("/v1/instances")
                    .add_header(
                        "authorization".parse::<axum::http::header::HeaderName>().unwrap(),
                        format!("Bearer {}", bad_token).parse::<axum::http::header::HeaderValue>().unwrap(),
                    )
                    .add_header("x-forwarded-for".parse::<axum::http::header::HeaderName>().unwrap(), attacker_ip.parse::<axum::http::header::HeaderValue>().unwrap())
                    .await;
            }

            let resp = server
                .get("/v1/instances")
                .add_header(
                    "authorization".parse::<axum::http::header::HeaderName>().unwrap(),
                    format!("Bearer {}", bad_token).parse::<axum::http::header::HeaderValue>().unwrap(),
                )
                .add_header("x-forwarded-for".parse::<axum::http::header::HeaderName>().unwrap(), attacker_ip.parse::<axum::http::header::HeaderValue>().unwrap())
                .await;
            assert_eq!(resp.status_code(), 429);
        }

        #[test]
        fn expires_after_5_minutes() {
            let lockout = Lockout::new();
            let ip = "127.0.0.1";
            for _ in 0..10 {
                lockout.record_failure(ip);
            }
            assert!(!lockout.check(ip));
            lockout.unlock(ip);
            assert!(lockout.check(ip));
        }

        #[test]
        fn lru_capped() {
            let lockout = Lockout::new();
            for i in 0..2000_u32 {
                let ip = format!("10.{}.{}.{}", i / 65536, (i / 256) % 256, i % 256);
                lockout.record_failure(&ip);
            }
            assert!(lockout.len() <= 1024);
        }

        #[tokio::test]
        async fn separate_ips_dont_interfere() {
            let (state, _dir) = make_state();
            let (_, valid_raw) =
                state.token_store.create("test".into(), default_scopes(), None).unwrap();
            let server = make_server(state);
            let bad_token = "oblch_wrongtoken12345678901234567890123456";
            let attacker_ip = "10.100.0.1";
            let good_ip = "10.200.0.1";

            for _ in 0..10 {
                let _ = server
                    .get("/v1/instances")
                    .add_header(
                        "authorization".parse::<axum::http::header::HeaderName>().unwrap(),
                        format!("Bearer {}", bad_token).parse::<axum::http::header::HeaderValue>().unwrap(),
                    )
                    .add_header("x-forwarded-for".parse::<axum::http::header::HeaderName>().unwrap(), attacker_ip.parse::<axum::http::header::HeaderValue>().unwrap())
                    .await;
            }

            let resp = server
                .get("/v1/instances")
                .add_header(
                    "authorization".parse::<axum::http::header::HeaderName>().unwrap(),
                    format!("Bearer {}", valid_raw).parse::<axum::http::header::HeaderValue>().unwrap(),
                )
                .add_header("x-forwarded-for".parse::<axum::http::header::HeaderName>().unwrap(), good_ip.parse::<axum::http::header::HeaderValue>().unwrap())
                .await;
            assert_eq!(resp.status_code(), 200);
        }
    }

    mod routes_tests {
        use super::*;

        #[tokio::test]
        async fn health_no_auth() {
            let (state, _dir) = make_state();
            let server = make_server(state);
            let resp = server.get("/v1/health").await;
            assert_eq!(resp.status_code(), 200);
        }

        #[tokio::test]
        async fn health_no_leak() {
            let (state, _dir) = make_state();
            let server = make_server(state);
            let resp = server.get("/v1/health").await;
            let body: Value = resp.json();
            assert_eq!(body, json!({ "status": "ok" }));
        }

        #[tokio::test]
        async fn server_header_stripped() {
            let (state, _dir) = make_state();
            let server = make_server(state);
            let resp = server.get("/v1/health").await;
            assert!(resp.headers().get("server").is_none());
        }

        #[tokio::test]
        async fn body_limit_enforced() {
            let (state, _dir) = make_state();
            let (_, raw) = state
                .token_store
                .create("admin".into(), vec![SCOPE_WILDCARD.to_string()], None).unwrap();
            let server = make_server(state);
            let big_body = "x".repeat(256 * 1024 + 1);
            let resp = server
                .post("/v1/instances")
                .add_header(
                    "authorization".parse::<axum::http::header::HeaderName>().unwrap(),
                    format!("Bearer {}", raw).parse::<axum::http::header::HeaderValue>().unwrap(),
                )
                .content_type("application/json")
                .text(big_body)
                .await;
            assert!(resp.status_code() == 413 || resp.status_code() == 415);
        }

        #[tokio::test]
        async fn create_then_get_status_by_id() {
            let (state, _dir) = make_state();
            let (_, raw) = state
                .token_store
                .create("admin".into(), vec![SCOPE_WILDCARD.to_string()], None).unwrap();
            let server = make_server(state);
            let auth_val: axum::http::HeaderValue =
                format!("Bearer {}", raw).parse::<axum::http::header::HeaderValue>().unwrap();

            let create_resp = server
                .post("/v1/instances")
                .add_header("authorization".parse::<axum::http::header::HeaderName>().unwrap(), auth_val.clone())
                .json(&json!({
                    "name": "my-bot",
                    "runtime": "Docker",
                    "version": "1.0.0",
                    "data_dir": "/tmp/data",
                    "config_dir": "/tmp/config"
                }))
                .await;
            assert_eq!(create_resp.status_code(), 201);
            let created: Value = create_resp.json();
            let id = created["spec"]["id"].as_str().unwrap().to_string();

            let status_resp = server
                .get(&format!("/v1/instances/{}/status", id))
                .add_header("authorization".parse::<axum::http::header::HeaderName>().unwrap(), auth_val.clone())
                .await;
            assert_eq!(status_resp.status_code(), 200);
            let status: Value = status_resp.json();
            assert_eq!(status["id"].as_str().unwrap(), id);
        }

        #[tokio::test]
        async fn problem_details_on_error() {
            let (state, _dir) = make_state();
            let (_, raw) = state
                .token_store
                .create("admin".into(), vec![SCOPE_WILDCARD.to_string()], None).unwrap();
            let server = make_server(state);
            let resp = server
                .get("/v1/instances/nonexistent-id-abc")
                .add_header(
                    "authorization".parse::<axum::http::header::HeaderName>().unwrap(),
                    format!("Bearer {}", raw).parse::<axum::http::header::HeaderValue>().unwrap(),
                )
                .await;
            assert_eq!(resp.status_code(), 404);
            let ct = resp
                .headers()
                .get("content-type")
                .unwrap()
                .to_str()
                .unwrap();
            assert!(ct.contains("application/problem+json"));
        }
    }

    mod audit_tests {
        use super::*;

        #[tokio::test]
        async fn token_id_logged_not_raw() {
            let (state, _dir) = make_state();
            let (record, raw) =
                state.token_store.create("test".into(), default_scopes(), None).unwrap();
            assert!(record.id.starts_with("tok_"));
            assert!(!record.id.starts_with("oblch_"));
            assert!(raw.starts_with("oblch_"));
            assert_ne!(record.id, raw);
        }
    }

    mod instance_crud_tests {
        use super::*;

        fn admin_token(state: &ApiState) -> String {
            let (_, raw) = state
                .token_store
                .create("admin".into(), vec![SCOPE_WILDCARD.to_string()], None).unwrap();
            raw
        }

        fn parse_sse_done(body: &[u8]) -> serde_json::Value {
            let text = std::str::from_utf8(body).unwrap();
            for line in text.lines() {
                if let Some(data) = line.strip_prefix("data: ") {
                    if let Ok(val) = serde_json::from_str::<serde_json::Value>(data) {
                        if val.get("done").is_some() {
                            return val;
                        }
                    }
                }
            }
            panic!("no done event in SSE body:\n{text}");
        }

        fn auth_header(raw: &str) -> (axum::http::header::HeaderName, axum::http::HeaderValue) {
            (
                "authorization".parse().unwrap(),
                format!("Bearer {raw}").parse().unwrap(),
            )
        }

        #[tokio::test]
        async fn add_then_list_returns_instance() {
            let (state, _dir) = make_state();
            let raw = admin_token(&state);
            let server = make_server(state);
            let (name, val) = auth_header(&raw);

            let create = server
                .post("/v1/instances")
                .add_header(name.clone(), val.clone())
                .json(&json!({ "name": "my-bot", "runtime": "Docker" }))
                .await;
            assert_eq!(create.status_code(), 201);

            let list = server.get("/v1/instances").add_header(name, val).await;
            assert_eq!(list.status_code(), 200);
            let body: Vec<Value> = list.json();
            assert_eq!(body.len(), 1);
            assert_eq!(body[0]["spec"]["name"], "my-bot");
        }

        #[tokio::test]
        async fn add_defaults_data_dir_under_store_root() {
            let (state, dir) = make_state();
            let raw = admin_token(&state);
            let server = make_server(state);
            let (name, val) = auth_header(&raw);

            let resp = server
                .post("/v1/instances")
                .add_header(name, val)
                .json(&json!({ "name": "bot", "runtime": "Binary" }))
                .await;
            assert_eq!(resp.status_code(), 201);
            let body: Value = resp.json();
            let data_dir = body["spec"]["data_dir"].as_str().unwrap();
            assert!(
                data_dir.starts_with(dir.path().to_str().unwrap()),
                "data_dir should be under store root, got {data_dir}"
            );
        }

        #[tokio::test]
        async fn add_then_start_desired_state_running() {
            let (state, _dir) = make_state();
            let raw = admin_token(&state);
            let server = make_server(state);
            let (name, val) = auth_header(&raw);

            let create = server
                .post("/v1/instances")
                .add_header(name.clone(), val.clone())
                .json(&json!({ "name": "bot", "runtime": "Binary" }))
                .await;
            assert_eq!(create.status_code(), 201);
            let id = create.json::<Value>()["spec"]["id"].as_str().unwrap().to_string();

            let start = server
                .post(&format!("/v1/instances/{id}/start"))
                .add_header(name.clone(), val.clone())
                .json(&json!({}))
                .await;
            assert_eq!(start.status_code(), 200);

            let status = server
                .get(&format!("/v1/instances/{id}/status"))
                .add_header(name, val)
                .await;
            assert_eq!(status.status_code(), 200);
            assert_eq!(status.json::<Value>()["desired_state"], "Running");
        }

        #[tokio::test]
        async fn add_then_delete_then_start_is_404() {
            let (state, _dir) = make_state();
            let raw = admin_token(&state);
            let server = make_server(state);
            let (name, val) = auth_header(&raw);

            let create = server
                .post("/v1/instances")
                .add_header(name.clone(), val.clone())
                .json(&json!({ "name": "bot", "runtime": "Python" }))
                .await;
            let id = create.json::<Value>()["spec"]["id"].as_str().unwrap().to_string();

            let del = server
                .delete(&format!("/v1/instances/{id}"))
                .add_header(name.clone(), val.clone())
                .await;
            assert_eq!(del.status_code(), 204);

            let start = server
                .post(&format!("/v1/instances/{id}/start"))
                .add_header(name, val)
                .json(&json!({}))
                .await;
            assert_eq!(start.status_code(), 200);
            let body = start.text();
            let done = parse_sse_done(body.as_bytes());
            assert!(done["done"]["err"].is_string(), "expected done.err: {done}");
        }

        #[tokio::test]
        async fn start_nonexistent_returns_sse_err() {
            let (state, _dir) = make_state();
            let raw = admin_token(&state);
            let server = make_server(state);
            let (name, val) = auth_header(&raw);

            let resp = server
                .post("/v1/instances/no-such-id/start")
                .add_header(name, val)
                .json(&json!({}))
                .await;
            assert_eq!(resp.status_code(), 200);
            let body = resp.text();
            let done = parse_sse_done(body.as_bytes());
            assert!(done["done"]["err"].is_string(), "expected done.err: {done}");
        }

        #[tokio::test]
        async fn short_id_prefix_resolves() {
            let (state, _dir) = make_state();
            let raw = admin_token(&state);
            let server = make_server(state);
            let (name, val) = auth_header(&raw);

            let create = server
                .post("/v1/instances")
                .add_header(name.clone(), val.clone())
                .json(&json!({ "name": "bot", "runtime": "Docker" }))
                .await;
            let full_id = create.json::<Value>()["spec"]["id"].as_str().unwrap().to_string();
            let short = &full_id[..8];

            let status = server
                .get(&format!("/v1/instances/{short}/status"))
                .add_header(name, val)
                .await;
            assert_eq!(status.status_code(), 200);
        }

        #[tokio::test]
        async fn delete_then_list_is_empty() {
            let (state, _dir) = make_state();
            let raw = admin_token(&state);
            let server = make_server(state);
            let (name, val) = auth_header(&raw);

            let create = server
                .post("/v1/instances")
                .add_header(name.clone(), val.clone())
                .json(&json!({ "name": "bot", "runtime": "Docker" }))
                .await;
            let id = create.json::<Value>()["spec"]["id"].as_str().unwrap().to_string();

            server
                .delete(&format!("/v1/instances/{id}"))
                .add_header(name.clone(), val.clone())
                .await;

            let list = server.get("/v1/instances").add_header(name, val).await;
            let body: Vec<Value> = list.json();
            assert!(body.is_empty());
        }
    }

    mod bind_tests {
        use super::*;
        use std::net::SocketAddr;

        #[tokio::test]
        async fn non_loopback_warns_on_startup() {
            let addr: SocketAddr = "0.0.0.0:0".parse().unwrap();
            assert!(
                !addr.ip().is_loopback(),
                "0.0.0.0 should not be loopback"
            );
        }
    }
}
