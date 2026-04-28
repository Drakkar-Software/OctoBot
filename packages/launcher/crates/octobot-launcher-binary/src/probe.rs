use octobot_launcher_core::model::HttpProbe;

pub(crate) async fn run_http_probe(url: &str) -> HttpProbe {
    let start = std::time::Instant::now();
    let result = reqwest::Client::new()
        .get(url)
        .timeout(std::time::Duration::from_secs(5))
        .send()
        .await;
    let latency_ms = u32::try_from(start.elapsed().as_millis()).unwrap_or(u32::MAX);
    HttpProbe {
        url: url.to_string(),
        status_code: result.as_ref().ok().map(|r| r.status().as_u16()),
        latency_ms: Some(latency_ms),
        at: chrono::Utc::now(),
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;
    use std::net::SocketAddr;
    use tokio::io::AsyncWriteExt;
    use tokio::net::TcpListener;

    async fn spawn_http_200_server() -> SocketAddr {
        let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let addr = listener.local_addr().unwrap();
        tokio::spawn(async move {
            if let Ok((mut stream, _)) = listener.accept().await {
                let response = b"HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n";
                let _ = stream.write_all(response).await;
            }
        });
        addr
    }

    #[tokio::test]
    async fn http_probe_records_status() {
        let addr = spawn_http_200_server().await;
        let url = format!("http://{addr}/health");
        let probe = run_http_probe(&url).await;
        assert_eq!(probe.status_code, Some(200));
        assert!(probe.latency_ms.is_some());
    }

    #[tokio::test]
    async fn http_probe_handles_unreachable() {
        let probe = run_http_probe("http://127.0.0.1:1/unreachable").await;
        assert_eq!(probe.status_code, None);
    }
}
