use anyhow::{Context, Result};
use serde::de::DeserializeOwned;

pub struct ApiResponse {
    pub status: u16,
    body: String,
}

impl ApiResponse {
    pub fn is_success(&self) -> bool {
        (200..300).contains(&self.status)
    }

    pub fn text(self) -> String {
        self.body
    }

    pub fn json<T: DeserializeOwned>(self) -> Result<T> {
        serde_json::from_str(&self.body).context("parse JSON response")
    }
}

pub struct ApiClient {
    base_url: String,
    token: Option<String>,
    client: reqwest::Client,
    #[cfg(unix)]
    socket_path: Option<std::path::PathBuf>,
}

impl std::fmt::Debug for ApiClient {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("ApiClient")
            .field("base_url", &self.base_url)
            .finish_non_exhaustive()
    }
}

impl ApiClient {
    pub fn new(api_bind: &str, token: Option<String>) -> Self {
        Self {
            base_url: format!("http://{api_bind}"),
            token,
            client: reqwest::Client::new(),
            #[cfg(unix)]
            socket_path: None,
        }
    }

    pub fn from_config(config: &octobot_launcher_config::LauncherConfig, token: Option<String>) -> Self {
        #[cfg(unix)]
        {
            let socket_path = config.launcher.data_root.join(octobot_launcher_config::SOCKET_FILENAME);
            if socket_path.exists() {
                return Self {
                    base_url: format!("http://{}", config.launcher.api_bind),
                    token,
                    client: reqwest::Client::new(),
                    socket_path: Some(socket_path),
                };
            }
        }
        Self::new(&config.launcher.api_bind, token)
    }

    pub async fn get(&self, path: &str) -> Result<ApiResponse> {
        #[cfg(unix)]
        if let Some(sock) = &self.socket_path {
            return unix_request(sock, "GET", path, None).await;
        }
        self.tcp_get(path).await
    }

    pub async fn post(&self, path: &str, body: serde_json::Value) -> Result<ApiResponse> {
        #[cfg(unix)]
        if let Some(sock) = &self.socket_path {
            return unix_request(sock, "POST", path, Some(body)).await;
        }
        self.tcp_post(path, body).await
    }

    pub async fn delete(&self, path: &str) -> Result<ApiResponse> {
        #[cfg(unix)]
        if let Some(sock) = &self.socket_path {
            return unix_request(sock, "DELETE", path, None).await;
        }
        self.tcp_delete(path).await
    }

    pub async fn post_sse(
        &self,
        path: &str,
        body: serde_json::Value,
        mut on_step: impl FnMut(&str),
    ) -> Result<serde_json::Value> {
        #[cfg(unix)]
        if let Some(sock) = &self.socket_path {
            return unix_post_sse(sock, path, body, &mut on_step).await;
        }
        self.tcp_post_sse(path, body, &mut on_step).await
    }

    async fn tcp_post_sse(
        &self,
        path: &str,
        body: serde_json::Value,
        on_step: &mut impl FnMut(&str),
    ) -> Result<serde_json::Value> {
        use futures_util::StreamExt;

        let mut req = self.client
            .post(format!("{}{}", self.base_url, path))
            .json(&body);
        if let Some(t) = &self.token {
            req = req.bearer_auth(t);
        }
        let resp = req.send().await.with_context(supervisor_not_running_msg)?;
        if !resp.status().is_success() {
            let status = resp.status().as_u16();
            let text = resp.text().await.unwrap_or_default();
            anyhow::bail!("HTTP {status}: {text}");
        }

        let mut stream = resp.bytes_stream();
        let mut buf = String::new();
        while let Some(chunk) = stream.next().await {
            let chunk = chunk.context("read SSE chunk")?;
            buf.push_str(&String::from_utf8_lossy(&chunk));
            if let Some(result) = drain_sse_events(&mut buf, on_step) {
                return result;
            }
        }
        anyhow::bail!("SSE stream ended without done event")
    }

    async fn tcp_get(&self, path: &str) -> Result<ApiResponse> {
        let mut req = self.client.get(format!("{}{}", self.base_url, path));
        if let Some(t) = &self.token {
            req = req.bearer_auth(t);
        }
        let resp = req.send().await.with_context(supervisor_not_running_msg)?;
        reqwest_to_api(resp).await
    }

    async fn tcp_post(&self, path: &str, body: serde_json::Value) -> Result<ApiResponse> {
        let mut req = self.client
            .post(format!("{}{}", self.base_url, path))
            .json(&body);
        if let Some(t) = &self.token {
            req = req.bearer_auth(t);
        }
        let resp = req.send().await.with_context(supervisor_not_running_msg)?;
        reqwest_to_api(resp).await
    }

    async fn tcp_delete(&self, path: &str) -> Result<ApiResponse> {
        let mut req = self.client.delete(format!("{}{}", self.base_url, path));
        if let Some(t) = &self.token {
            req = req.bearer_auth(t);
        }
        let resp = req.send().await.with_context(supervisor_not_running_msg)?;
        reqwest_to_api(resp).await
    }
}

async fn reqwest_to_api(resp: reqwest::Response) -> Result<ApiResponse> {
    let status = resp.status().as_u16();
    let body = resp.text().await.context("read response body")?;
    Ok(ApiResponse { status, body })
}

#[cfg(unix)]
async fn unix_request(
    socket_path: &std::path::Path,
    method: &str,
    path: &str,
    body: Option<serde_json::Value>,
) -> Result<ApiResponse> {
    use bytes::Bytes;
    use http_body_util::{BodyExt, Full};
    use hyper::Request;
    use hyper_util::rt::TokioIo;
    use tokio::net::UnixStream;

    let stream = UnixStream::connect(socket_path).await
        .context("connect to launcher unix socket")?;
    let io = TokioIo::new(stream);
    let (mut sender, conn) = hyper::client::conn::http1::handshake(io).await
        .context("http1 handshake")?;
    tokio::spawn(conn);

    let (body_bytes, content_type) = match body {
        Some(json) => (Bytes::from(serde_json::to_string(&json)?), Some("application/json")),
        None => (Bytes::new(), None),
    };

    let mut builder = Request::builder()
        .method(method)
        .uri(format!("http://launcher{path}"))
        .header("Host", "launcher");
    if let Some(ct) = content_type {
        builder = builder.header("Content-Type", ct);
    }
    let req = builder.body(Full::new(body_bytes)).unwrap();

    let resp = sender.send_request(req).await.context("send request")?;
    let status = resp.status().as_u16();
    let body_bytes = resp.into_body().collect().await.context("read response body")?.to_bytes();
    Ok(ApiResponse {
        status,
        body: String::from_utf8_lossy(&body_bytes).into_owned(),
    })
}

fn drain_sse_events(buf: &mut String, on_step: &mut impl FnMut(&str)) -> Option<Result<serde_json::Value>> {
    loop {
        let pos = buf.find("\n\n")?;
        let frame: String = buf.drain(..pos + 2).collect();
        for line in frame.lines() {
            let Some(data) = line.strip_prefix("data: ") else { continue };
            if let Ok(val) = serde_json::from_str::<serde_json::Value>(data) {
                if let Some(done) = val.get("done") {
                    if let Some(err) = done.get("err").and_then(|v| v.as_str()) {
                        return Some(Err(anyhow::anyhow!("{err}")));
                    }
                    return Some(Ok(done.get("ok").cloned().unwrap_or(serde_json::Value::Null)));
                }
            }
            // plain string or non-done JSON both reach the spinner
            on_step(data);
        }
    }
}

#[cfg(unix)]
async fn unix_post_sse(
    socket_path: &std::path::Path,
    path: &str,
    body: serde_json::Value,
    on_step: &mut impl FnMut(&str),
) -> Result<serde_json::Value> {
    use bytes::Bytes;
    use http_body_util::{BodyDataStream, Full};
    use hyper::Request;
    use hyper_util::rt::TokioIo;
    use futures_util::StreamExt;
    use tokio::net::UnixStream;

    let stream = UnixStream::connect(socket_path).await
        .context("connect to launcher unix socket")?;
    let io = TokioIo::new(stream);
    let (mut sender, conn) = hyper::client::conn::http1::handshake(io).await
        .context("http1 handshake")?;
    tokio::spawn(conn);

    let body_bytes = Bytes::from(serde_json::to_string(&body)?);
    let req = Request::builder()
        .method("POST")
        .uri(format!("http://launcher{path}"))
        .header("Host", "launcher")
        .header("Content-Type", "application/json")
        .body(Full::new(body_bytes))
        .unwrap();

    let resp = sender.send_request(req).await.context("send request")?;
    if !resp.status().is_success() {
        let status = resp.status().as_u16();
        use http_body_util::BodyExt;
        let body = resp.into_body().collect().await.context("read error body")?.to_bytes();
        anyhow::bail!("HTTP {status}: {}", String::from_utf8_lossy(&body));
    }
    let mut data_stream = Box::pin(BodyDataStream::new(resp.into_body()));
    let mut buf = String::new();
    while let Some(chunk) = data_stream.next().await {
        let data = chunk.context("read SSE chunk")?;
        buf.push_str(&String::from_utf8_lossy(&data));
        if let Some(result) = drain_sse_events(&mut buf, on_step) {
            return result;
        }
    }
    anyhow::bail!("SSE stream ended without done event")
}

fn supervisor_not_running_msg() -> String {
    "Supervisor not running. Start with: octobot-launcher service start".to_string()
}
