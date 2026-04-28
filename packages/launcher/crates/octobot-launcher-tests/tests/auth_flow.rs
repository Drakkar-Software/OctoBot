#![allow(clippy::unwrap_used, clippy::expect_used)]

use std::sync::Arc;

use axum_test::TestServer;
use octobot_launcher_api::{
    ApiState,
    auth::LocalSocketMarker,
    lockout::Lockout,
    router,
    token_store::TokenStore,
};
use octobot_launcher_config::Store;
use tempfile::TempDir;

fn make_state() -> (ApiState, TempDir) {
    let dir = TempDir::new().expect("tempdir");
    let store = Arc::new(Store::new(dir.path().to_path_buf()).expect("store"));
    let token_store = Arc::new(TokenStore::load(dir.path().join("tokens.json")));
    let lockout = Arc::new(Lockout::new());
    (
        ApiState {
            store,
            token_store,
            lockout,
            backends: Arc::new(vec![]),
        },
        dir,
    )
}

fn make_server(state: ApiState) -> TestServer {
    TestServer::new(router(state))
}

fn auth_header(raw: &str) -> (axum::http::HeaderName, axum::http::HeaderValue) {
    (
        "authorization".parse().unwrap(),
        format!("Bearer {raw}").parse().unwrap(),
    )
}

#[tokio::test]
async fn end_to_end_token_flow() {
    let (state, _dir) = make_state();

    let bootstrap_raw = state.token_store.bootstrap_if_empty().expect("bootstrap token").expect("should have token");

    let server = make_server(state.clone());

    let (name, value) = auth_header(&bootstrap_raw);
    let resp = server.get("/v1/instances").add_header(name, value).await;
    assert_eq!(resp.status_code(), 200);

    let (name, value) = auth_header(&bootstrap_raw);
    let create_resp = server
        .post("/v1/tokens")
        .add_header(name, value)
        .json(&serde_json::json!({ "label": "new-token" }))
        .await;
    assert_eq!(create_resp.status_code(), 201);
    let body: serde_json::Value = create_resp.json();
    let new_raw = body["raw_token"].as_str().expect("raw_token field").to_string();
    let new_id = body["token"]["id"].as_str().expect("token.id field").to_string();

    let (name, value) = auth_header(&new_raw);
    let resp2 = server.get("/v1/instances").add_header(name, value).await;
    assert_eq!(resp2.status_code(), 200);

    let (name, value) = auth_header(&bootstrap_raw);
    let revoke_resp = server
        .delete(&format!("/v1/tokens/{new_id}"))
        .add_header(name, value)
        .await;
    assert_eq!(revoke_resp.status_code(), 204);

    let (name, value) = auth_header(&new_raw);
    let resp3 = server.get("/v1/instances").add_header(name, value).await;
    assert_eq!(resp3.status_code(), 401);
}

#[tokio::test]
async fn brute_force_locks_ip() {
    let (state, _dir) = make_state();
    let server = make_server(state);

    let bad_token = "oblch_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";

    for _ in 0..10 {
        let (name, value) = auth_header(bad_token);
        server.get("/v1/instances").add_header(name, value).await;
    }

    let (name, value) = auth_header(bad_token);
    let resp = server.get("/v1/instances").add_header(name, value).await;
    assert_eq!(resp.status_code(), 429);
}

#[tokio::test]
async fn unix_socket_immune_to_lockout() {
    use axum::{body::Body, extract::Request, middleware, response::Response};

    let (state, _dir) = make_state();

    async fn inject_local(mut req: Request<Body>, next: middleware::Next) -> Response {
        req.extensions_mut().insert(LocalSocketMarker);
        next.run(req).await
    }

    let app = router(state).layer(middleware::from_fn(inject_local));
    let server = TestServer::new(app);

    for _ in 0..11 {
        let resp = server.get("/v1/instances").await;
        assert_eq!(resp.status_code(), 200);
    }
}
