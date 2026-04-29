use std::collections::BTreeMap;
use std::convert::Infallible;
use std::path::PathBuf;
use std::pin::Pin;
use std::sync::Arc;
use std::time::Duration;

use axum::{
    Json,
    extract::{Path, State},
    http::StatusCode,
    response::{IntoResponse, Response, sse::{Event, KeepAlive, Sse}},
};
use futures_util::{FutureExt, Stream};
use octobot_launcher_config::{DesiredState, InstanceRecord, Store};
use octobot_launcher_core::backend::Backend;
use octobot_launcher_core::error::LauncherError;
use octobot_launcher_core::{InstanceId, InstanceSpec, InstanceState, RuntimeKind};
use octobot_launcher_core::model::PortMapping;
use serde::Deserialize;
use serde_json::json;
use tokio_stream::wrappers::UnboundedReceiverStream;
use tokio_stream::StreamExt as TokioStreamExt;

use crate::error::ApiError;

#[allow(missing_debug_implementations)]
#[derive(Clone)]
pub struct InstanceActionState {
    pub store: Arc<Store>,
    pub backends: Arc<Vec<Box<dyn Backend>>>,
}

#[derive(Debug, Deserialize)]
pub struct CreateInstanceBody {
    pub name: String,
    pub runtime: RuntimeKind,
    #[serde(default = "default_version")]
    pub version: String,
    pub data_dir: Option<PathBuf>,
    pub config_dir: Option<PathBuf>,
    #[serde(default)]
    pub env: BTreeMap<String, String>,
    #[serde(default)]
    pub ports: Vec<PortMapping>,
    #[serde(default)]
    pub auto_restart: bool,
    #[serde(default)]
    pub auto_update: bool,
    #[serde(default)]
    pub runtime_options: serde_json::Value,
}

fn default_version() -> String {
    "latest".to_string()
}

#[derive(Debug, Deserialize, Default)]
pub struct PatchInstanceBody {
    pub name: Option<String>,
    pub version: Option<String>,
    pub auto_restart: Option<bool>,
    pub auto_update: Option<bool>,
    pub env: Option<BTreeMap<String, String>>,
    pub runtime_options: Option<serde_json::Value>,
}

type EventStream = Pin<Box<dyn Stream<Item = Result<Event, Infallible>> + Send>>;

fn error_stream(msg: impl Into<String>) -> impl IntoResponse {
    let data = json!({"done": {"err": msg.into()}}).to_string();
    let stream: EventStream =
        Box::pin(tokio_stream::once(Ok(Event::default().data(data))));
    Sse::new(stream)
}

fn progress_stream(rx: tokio::sync::mpsc::UnboundedReceiver<String>) -> impl IntoResponse {
    let stream: EventStream = Box::pin(
        UnboundedReceiverStream::new(rx)
            .map(|data| Ok(Event::default().data(data))),
    );
    Sse::new(stream).keep_alive(
        KeepAlive::new()
            .interval(Duration::from_secs(15))
            .text("heartbeat"),
    )
}

fn panic_message(p: &Box<dyn std::any::Any + Send>) -> String {
    if let Some(s) = p.downcast_ref::<&'static str>() {
        return (*s).to_string();
    }
    if let Some(s) = p.downcast_ref::<String>() {
        return s.clone();
    }
    "unknown panic".to_string()
}

pub async fn list_instances(
    State(store): State<Arc<Store>>,
) -> Result<impl IntoResponse, ApiError> {
    let records = store
        .list_instance_records()
        .map_err(|e| ApiError::Internal(e.to_string()))?;
    Ok(Json(records))
}

pub async fn create_instance(
    State(store): State<Arc<Store>>,
    Json(body): Json<CreateInstanceBody>,
) -> Result<impl IntoResponse, ApiError> {
    let id = InstanceId::new();
    let data_dir = body.data_dir.unwrap_or_else(|| {
        store.data_root().join("instances").join(id.0.to_string())
    });
    let config_dir = body.config_dir.unwrap_or_else(|| data_dir.join("config"));
    let spec = InstanceSpec {
        id,
        name: body.name,
        runtime: body.runtime,
        version: body.version,
        data_dir,
        config_dir,
        env: body.env,
        ports: body.ports,
        auto_restart: body.auto_restart,
        auto_update: body.auto_update,
        runtime_options: body.runtime_options,
    };
    let record = InstanceRecord {
        spec: spec.clone(),
        desired_state: DesiredState::Stopped,
        last_known_state: InstanceState::Stopped,
        created_at: chrono::Utc::now(),
        updated_at: chrono::Utc::now(),
    };

    let path = store.instances_dir().join(format!("{}.json", spec.id.0));
    store
        .write_atomic(&path, &record)
        .map_err(|e| ApiError::Internal(e.to_string()))?;

    Ok((StatusCode::CREATED, Json(record)))
}

pub async fn get_instance(
    State(store): State<Arc<Store>>,
    Path(id): Path<String>,
) -> Result<impl IntoResponse, ApiError> {
    let record = find_instance(&store, &id)?;
    Ok(Json(record))
}

pub async fn patch_instance(
    State(store): State<Arc<Store>>,
    Path(id): Path<String>,
    Json(body): Json<PatchInstanceBody>,
) -> Result<impl IntoResponse, ApiError> {
    let mut record = find_instance(&store, &id)?;

    if let Some(name) = body.name {
        record.spec.name = name;
    }
    if let Some(version) = body.version {
        record.spec.version = version;
    }
    if let Some(auto_restart) = body.auto_restart {
        record.spec.auto_restart = auto_restart;
    }
    if let Some(auto_update) = body.auto_update {
        record.spec.auto_update = auto_update;
    }
    if let Some(env) = body.env {
        record.spec.env = env;
    }
    if let Some(runtime_options) = body.runtime_options {
        record.spec.runtime_options = runtime_options;
    }
    record.updated_at = chrono::Utc::now();

    let path = store.instances_dir().join(format!("{}.json", record.spec.id.0));
    store
        .write_atomic(&path, &record)
        .map_err(|e| ApiError::Internal(e.to_string()))?;

    Ok(Json(record))
}

pub async fn delete_instance(
    State(store): State<Arc<Store>>,
    Path(id): Path<String>,
) -> Result<impl IntoResponse, ApiError> {
    let record = find_instance(&store, &id)?;
    let path = store.instances_dir().join(format!("{}.json", record.spec.id.0));
    store
        .delete(&path)
        .map_err(|e| ApiError::Internal(e.to_string()))?;
    Ok(StatusCode::NO_CONTENT)
}

pub async fn start_instance(
    State(state): State<InstanceActionState>,
    Path(id): Path<String>,
) -> Response {
    let record = match find_instance(&state.store, &id) {
        Ok(r) => r,
        Err(e) => return error_stream(e.to_string()).into_response(),
    };
    let runtime = record.spec.runtime;
    if !state.backends.iter().any(|b| b.kind() == runtime) {
        return error_stream(format!("no backend for runtime {runtime:?}")).into_response();
    }

    let (tx, rx) = tokio::sync::mpsc::unbounded_channel::<String>();
    let backends = state.backends.clone();
    let store = state.store.clone();

    tokio::spawn(async move {
        let backend = match backends.iter().find(|b| b.kind() == runtime) {
            Some(b) => b,
            None => {
                let _ = tx.send(json!({"done": {"err": "no backend"}}).to_string());
                return;
            }
        };
        let spec_id = record.spec.id;
        let result = std::panic::AssertUnwindSafe(backend.start(&record.spec, Some(&tx)))
            .catch_unwind()
            .await;
        match result {
            Ok(Ok(())) => {
                let records = store.list_instance_records().unwrap_or_default();
                let mut record = match records.into_iter().find(|r| r.spec.id == spec_id) {
                    Some(r) => r,
                    None => {
                        let _ = tx.send(json!({"done": {"err": "instance not found after start"}}).to_string());
                        return;
                    }
                };
                record.desired_state = DesiredState::Running;
                if let Ok(health) = backend.status(spec_id).await {
                    record.last_known_state = health.state;
                }
                record.updated_at = chrono::Utc::now();
                let path = store.instances_dir().join(format!("{}.json", record.spec.id.0));
                if let Err(e) = store.write_atomic(&path, &record) {
                    let _ = tx.send(json!({"done": {"err": e.to_string()}}).to_string());
                    return;
                }
                let _ = tx.send(json!({"done": {"ok": record}}).to_string());
            }
            Ok(Err(e)) => {
                let _ = tx.send(json!({"done": {"err": e.to_string()}}).to_string());
            }
            Err(panic) => {
                let msg = panic_message(&panic);
                let _ = tx.send(json!({"done": {"err": format!("daemon panic: {msg}")}}).to_string());
            }
        }
    });

    progress_stream(rx).into_response()
}

pub async fn stop_instance(
    State(state): State<InstanceActionState>,
    Path(id): Path<String>,
) -> Result<impl IntoResponse, ApiError> {
    let mut record = find_instance(&state.store, &id)?;
    let backend = state
        .backends
        .iter()
        .find(|b| b.kind() == record.spec.runtime)
        .ok_or_else(|| ApiError::ServiceUnavailable(format!("no backend for runtime {:?}", record.spec.runtime)))?;
    match backend.stop(&record.spec, Duration::from_secs(10)).await {
        Ok(()) | Err(LauncherError::NotRunning) => {}
        Err(e) => return Err(ApiError::Internal(e.to_string())),
    }
    record.desired_state = DesiredState::Stopped;
    record.updated_at = chrono::Utc::now();
    let path = state.store.instances_dir().join(format!("{}.json", record.spec.id.0));
    state
        .store
        .write_atomic(&path, &record)
        .map_err(|e| ApiError::Internal(e.to_string()))?;
    Ok(Json(record))
}

pub async fn restart_instance(
    State(state): State<InstanceActionState>,
    Path(id): Path<String>,
) -> Response {
    let record = match find_instance(&state.store, &id) {
        Ok(r) => r,
        Err(e) => return error_stream(e.to_string()).into_response(),
    };
    let runtime = record.spec.runtime;
    if !state.backends.iter().any(|b| b.kind() == runtime) {
        return error_stream(format!("no backend for runtime {runtime:?}")).into_response();
    }

    let (tx, rx) = tokio::sync::mpsc::unbounded_channel::<String>();
    let backends = state.backends.clone();
    let store = state.store.clone();

    tokio::spawn(async move {
        let backend = match backends.iter().find(|b| b.kind() == runtime) {
            Some(b) => b,
            None => {
                let _ = tx.send(json!({"done": {"err": "no backend"}}).to_string());
                return;
            }
        };
        let spec_id = record.spec.id;
        let result = std::panic::AssertUnwindSafe(
            backend.restart(&record.spec, Duration::from_secs(10), Some(&tx)),
        )
        .catch_unwind()
        .await;
        match result {
            Ok(Ok(())) => {
                let records = store.list_instance_records().unwrap_or_default();
                let mut record = match records.into_iter().find(|r| r.spec.id == spec_id) {
                    Some(r) => r,
                    None => {
                        let _ = tx.send(json!({"done": {"err": "instance not found after restart"}}).to_string());
                        return;
                    }
                };
                record.desired_state = DesiredState::Running;
                record.updated_at = chrono::Utc::now();
                let path = store.instances_dir().join(format!("{}.json", record.spec.id.0));
                if let Err(e) = store.write_atomic(&path, &record) {
                    let _ = tx.send(json!({"done": {"err": e.to_string()}}).to_string());
                    return;
                }
                let _ = tx.send(json!({"done": {"ok": record}}).to_string());
            }
            Ok(Err(e)) => {
                let _ = tx.send(json!({"done": {"err": e.to_string()}}).to_string());
            }
            Err(panic) => {
                let msg = panic_message(&panic);
                let _ = tx.send(json!({"done": {"err": format!("daemon panic: {msg}")}}).to_string());
            }
        }
    });

    progress_stream(rx).into_response()
}

pub async fn update_instance(
    State(state): State<InstanceActionState>,
    Path(id): Path<String>,
    Json(body): Json<serde_json::Value>,
) -> Response {
    let record = match find_instance(&state.store, &id) {
        Ok(r) => r,
        Err(e) => return error_stream(e.to_string()).into_response(),
    };
    let runtime = record.spec.runtime;
    if !state.backends.iter().any(|b| b.kind() == runtime) {
        return error_stream(format!("no backend for runtime {runtime:?}")).into_response();
    }

    let target_version = body
        .get("version")
        .and_then(|v| v.as_str())
        .unwrap_or(&record.spec.version)
        .to_string();

    let (tx, rx) = tokio::sync::mpsc::unbounded_channel::<String>();
    let backends = state.backends.clone();
    let store = state.store.clone();

    tokio::spawn(async move {
        let backend = match backends.iter().find(|b| b.kind() == runtime) {
            Some(b) => b,
            None => {
                let _ = tx.send(json!({"done": {"err": "no backend"}}).to_string());
                return;
            }
        };
        let spec_id = record.spec.id;
        let result = std::panic::AssertUnwindSafe(
            backend.update(&record.spec, &target_version, Some(&tx)),
        )
        .catch_unwind()
        .await;
        match result {
            Ok(Ok(())) => {
                let records = store.list_instance_records().unwrap_or_default();
                let mut record = match records.into_iter().find(|r| r.spec.id == spec_id) {
                    Some(r) => r,
                    None => {
                        let _ = tx.send(json!({"done": {"err": "instance not found after update"}}).to_string());
                        return;
                    }
                };
                record.spec.version = target_version;
                record.desired_state = DesiredState::Running;
                record.updated_at = chrono::Utc::now();
                let path = store.instances_dir().join(format!("{}.json", record.spec.id.0));
                if let Err(e) = store.write_atomic(&path, &record) {
                    let _ = tx.send(json!({"done": {"err": e.to_string()}}).to_string());
                    return;
                }
                let _ = tx.send(json!({"done": {"ok": record}}).to_string());
            }
            Ok(Err(e)) => {
                let _ = tx.send(json!({"done": {"err": e.to_string()}}).to_string());
            }
            Err(panic) => {
                let msg = panic_message(&panic);
                let _ = tx.send(json!({"done": {"err": format!("daemon panic: {msg}")}}).to_string());
            }
        }
    });

    progress_stream(rx).into_response()
}

pub async fn instance_status(
    State(store): State<Arc<Store>>,
    Path(id): Path<String>,
) -> Result<impl IntoResponse, ApiError> {
    let record = find_instance(&store, &id)?;
    Ok(Json(json!({
        "id": record.spec.id.0,
        "state": record.last_known_state,
        "desired_state": record.desired_state,
    })))
}

fn find_instance(store: &Store, id: &str) -> Result<InstanceRecord, ApiError> {
    let records = store
        .list_instance_records()
        .map_err(|e| ApiError::Internal(e.to_string()))?;

    if let Some(record) = records.iter().find(|r| r.spec.id.0.to_string() == id) {
        return Ok(record.clone());
    }

    let mut matches: Vec<InstanceRecord> = records
        .into_iter()
        .filter(|r| r.spec.id.0.to_string().starts_with(id))
        .collect();

    match matches.len() {
        0 => Err(ApiError::NotFound(format!("instance '{id}' not found"))),
        1 => Ok(matches.remove(0)),
        _ => Err(ApiError::BadRequest(format!(
            "ambiguous id prefix '{id}': multiple instances match"
        ))),
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used, clippy::expect_used)]
mod tests {
    use super::*;
    use axum::body::to_bytes;
    use axum::http::Request;
    use axum::Router;
    use axum::routing::post;
    use octobot_launcher_core::backend::mock::MockBackend;
    use octobot_launcher_config::Store;
    use std::collections::BTreeMap;
    use std::path::PathBuf;
    use tempfile::TempDir;

    fn make_state(dir: &TempDir) -> InstanceActionState {
        let store = Arc::new(Store::new(dir.path().to_path_buf()).unwrap());
        let backends: Arc<Vec<Box<dyn Backend>>> = Arc::new(vec![Box::new(MockBackend::default())]);
        InstanceActionState { store, backends }
    }

    fn make_record(store: &Store) -> InstanceRecord {
        let id = InstanceId::new();
        let spec = InstanceSpec {
            id,
            name: "test".into(),
            runtime: RuntimeKind::Binary,
            version: "1.0.0".into(),
            data_dir: PathBuf::from("/tmp/data"),
            config_dir: PathBuf::from("/tmp/config"),
            env: BTreeMap::new(),
            ports: vec![],
            auto_restart: false,
            auto_update: false,
            runtime_options: serde_json::Value::Null,
        };
        let record = InstanceRecord {
            spec: spec.clone(),
            desired_state: DesiredState::Stopped,
            last_known_state: InstanceState::Stopped,
            created_at: chrono::Utc::now(),
            updated_at: chrono::Utc::now(),
        };
        let path = store.instances_dir().join(format!("{}.json", spec.id.0));
        store.write_atomic(&path, &record).unwrap();
        record
    }

    fn parse_sse_done(body: &[u8]) -> serde_json::Value {
        let text = std::str::from_utf8(body).unwrap();
        for line in text.lines() {
            if let Some(data) = line.strip_prefix("data: ") {
                let val: serde_json::Value = serde_json::from_str(data).unwrap();
                if val.get("done").is_some() {
                    return val;
                }
            }
        }
        panic!("no done event in SSE body:\n{text}");
    }

    #[tokio::test]
    async fn start_instance_sse_emits_done_ok() {
        let dir = TempDir::new().unwrap();
        let state = make_state(&dir);
        let record = make_record(&state.store);
        let id = record.spec.id.0.to_string();

        let router = Router::new()
            .route("/instances/{id}/start", post(start_instance))
            .with_state(state);

        let req = Request::builder()
            .method("POST")
            .uri(format!("/instances/{id}/start"))
            .header("content-type", "application/json")
            .body(axum::body::Body::from("{}"))
            .unwrap();

        let resp = tower::ServiceExt::oneshot(router, req).await.unwrap();
        assert_eq!(resp.status(), 200);

        let body = to_bytes(resp.into_body(), usize::MAX).await.unwrap();
        let done = parse_sse_done(&body);
        assert!(done["done"]["ok"].is_object(), "expected done.ok: {done}");
    }

    #[tokio::test]
    async fn start_instance_sse_unknown_id_emits_done_err() {
        let dir = TempDir::new().unwrap();
        let state = make_state(&dir);

        let router = Router::new()
            .route("/instances/{id}/start", post(start_instance))
            .with_state(state);

        let req = Request::builder()
            .method("POST")
            .uri("/instances/00000000-0000-0000-0000-000000000000/start")
            .header("content-type", "application/json")
            .body(axum::body::Body::from("{}"))
            .unwrap();

        let resp = tower::ServiceExt::oneshot(router, req).await.unwrap();
        let body = to_bytes(resp.into_body(), usize::MAX).await.unwrap();
        let done = parse_sse_done(&body);
        assert!(done["done"]["err"].is_string(), "expected done.err: {done}");
    }
}
