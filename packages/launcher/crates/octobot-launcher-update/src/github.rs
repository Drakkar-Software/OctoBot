use std::path::{Path, PathBuf};

use serde::Deserialize;

use crate::error::{Result, UpdateError};

const GITHUB_API_LATEST: &str =
    "https://api.github.com/repos/Drakkar-Software/OctoBot/releases/latest";

const ASSET_MACOS_ARM64: &str = "OctoBot_macos_arm64";
const ASSET_MACOS_X64: &str = "OctoBot_macos_x64";
const ASSET_LINUX_ARM64: &str = "OctoBot_linux_arm64";
const ASSET_LINUX_X64: &str = "OctoBot_linux_x64";
const ASSET_WINDOWS_X64: &str = "OctoBot_windows_x64.exe";

#[derive(Deserialize)]
struct GithubRelease {
    tag_name: String,
    assets: Vec<GithubAsset>,
}

#[derive(Deserialize)]
struct GithubAsset {
    name: String,
    browser_download_url: String,
}

fn platform_asset_name() -> Option<&'static str> {
    match (std::env::consts::OS, std::env::consts::ARCH) {
        ("macos", "aarch64") => Some(ASSET_MACOS_ARM64),
        ("macos", "x86_64") => Some(ASSET_MACOS_X64),
        ("linux", "aarch64") => Some(ASSET_LINUX_ARM64),
        ("linux", "x86_64") => Some(ASSET_LINUX_X64),
        ("windows", "x86_64") => Some(ASSET_WINDOWS_X64),
        _ => None,
    }
}

pub async fn fetch_latest_octobot_binary(dest_dir: &Path) -> Result<PathBuf> {
    let client = reqwest::Client::builder()
        .user_agent(concat!("octobot-launcher/", env!("CARGO_PKG_VERSION")))
        .build()
        .map_err(|e| UpdateError::Network(e.to_string()))?;

    let asset_name = platform_asset_name().ok_or_else(|| {
        UpdateError::NoArtifactForPlatform(format!(
            "{}-{}",
            std::env::consts::OS,
            std::env::consts::ARCH
        ))
    })?;

    let release: GithubRelease = client
        .get(GITHUB_API_LATEST)
        .send()
        .await
        .map_err(|e| UpdateError::Network(e.to_string()))?
        .json()
        .await
        .map_err(|e| UpdateError::Network(e.to_string()))?;

    let asset = release
        .assets
        .iter()
        .find(|a| a.name == asset_name)
        .ok_or_else(|| UpdateError::NoArtifactForPlatform(asset_name.to_string()))?;

    tracing::info!(
        version = release.tag_name.as_str(),
        asset = asset_name,
        "downloading OctoBot from GitHub"
    );

    std::fs::create_dir_all(dest_dir)?;

    let dest_path = dest_dir.join(asset_name);
    download_to_file(&client, &asset.browser_download_url, &dest_path).await?;

    Ok(dest_path)
}

async fn download_to_file(client: &reqwest::Client, url: &str, dest: &Path) -> Result<()> {
    use tokio::io::AsyncWriteExt;

    let resp = client
        .get(url)
        .send()
        .await
        .map_err(|e| UpdateError::Network(e.to_string()))?;

    if !resp.status().is_success() {
        return Err(UpdateError::Network(format!(
            "download failed: HTTP {}",
            resp.status()
        )));
    }

    let mut file = tokio::fs::File::create(dest).await?;

    let bytes = resp
        .bytes()
        .await
        .map_err(|e| UpdateError::Network(e.to_string()))?;

    file.write_all(&bytes).await?;
    file.flush().await?;

    Ok(())
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;
    use wiremock::matchers::{method, path};
    use wiremock::{Mock, MockServer, ResponseTemplate};

    #[test]
    fn platform_asset_name_known_platform() {
        // The test machine is a known platform — we should always get a name.
        let name = platform_asset_name();
        assert!(
            name.is_some(),
            "no asset name for {}-{}",
            std::env::consts::OS,
            std::env::consts::ARCH
        );
    }

    #[test]
    fn platform_asset_name_macos_arm64() {
        assert_eq!(ASSET_MACOS_ARM64, "OctoBot_macos_arm64");
        assert_eq!(ASSET_MACOS_X64, "OctoBot_macos_x64");
        assert_eq!(ASSET_LINUX_ARM64, "OctoBot_linux_arm64");
        assert_eq!(ASSET_LINUX_X64, "OctoBot_linux_x64");
        assert_eq!(ASSET_WINDOWS_X64, "OctoBot_windows_x64.exe");
    }

    fn make_release_json(asset_name: &str, download_url: &str) -> serde_json::Value {
        serde_json::json!({
            "tag_name": "2.1.0",
            "assets": [{
                "name": asset_name,
                "browser_download_url": download_url
            }]
        })
    }

    #[tokio::test]
    async fn download_file_writes_bytes() {
        let server = MockServer::start().await;
        let content = b"fake octobot binary";
        Mock::given(method("GET"))
            .and(path("/download/octobot"))
            .respond_with(ResponseTemplate::new(200).set_body_bytes(content.as_slice()))
            .mount(&server)
            .await;

        let tmp = tempfile::tempdir().unwrap();
        let dest = tmp.path().join("octobot");
        let client = reqwest::Client::new();
        let url = format!("{}/download/octobot", server.uri());
        download_to_file(&client, &url, &dest).await.unwrap();

        assert_eq!(std::fs::read(&dest).unwrap(), content);
    }

    #[tokio::test]
    async fn download_file_fails_on_http_error() {
        let server = MockServer::start().await;
        Mock::given(method("GET"))
            .and(path("/download/octobot"))
            .respond_with(ResponseTemplate::new(404))
            .mount(&server)
            .await;

        let tmp = tempfile::tempdir().unwrap();
        let dest = tmp.path().join("octobot");
        let client = reqwest::Client::new();
        let url = format!("{}/download/octobot", server.uri());
        let result = download_to_file(&client, &url, &dest).await;
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn fetch_finds_asset_for_current_platform() {
        let server = MockServer::start().await;
        let asset_name = platform_asset_name().unwrap();
        let download_url = format!("{}/download/{asset_name}", server.uri());

        Mock::given(method("GET"))
            .and(path("/repos/Drakkar-Software/OctoBot/releases/latest"))
            .respond_with(
                ResponseTemplate::new(200)
                    .set_body_json(make_release_json(asset_name, &download_url)),
            )
            .mount(&server)
            .await;
        Mock::given(method("GET"))
            .and(path(format!("/download/{asset_name}")))
            .respond_with(ResponseTemplate::new(200).set_body_bytes(b"fake".as_slice()))
            .mount(&server)
            .await;

        // We can't easily override the GitHub URL, so test component-by-component.
        // Here we verify the JSON parsing and asset selection logic works end-to-end
        // using the download helper directly.
        let tmp = tempfile::tempdir().unwrap();
        let release_url = format!("{}/repos/Drakkar-Software/OctoBot/releases/latest", server.uri());
        let client = reqwest::Client::new();
        let release: GithubRelease = client.get(&release_url).send().await.unwrap().json().await.unwrap();

        assert_eq!(release.tag_name, "2.1.0");
        let asset = release.assets.iter().find(|a| a.name == asset_name).unwrap();
        let dest = tmp.path().join(asset_name);
        download_to_file(&client, &asset.browser_download_url, &dest).await.unwrap();
        assert_eq!(std::fs::read(&dest).unwrap(), b"fake");
    }

    #[tokio::test]
    async fn fetch_errors_when_asset_missing_for_platform() {
        let server = MockServer::start().await;
        Mock::given(method("GET"))
            .and(path("/repos/Drakkar-Software/OctoBot/releases/latest"))
            .respond_with(
                ResponseTemplate::new(200)
                    .set_body_json(serde_json::json!({
                        "tag_name": "2.1.0",
                        "assets": []
                    })),
            )
            .mount(&server)
            .await;

        let client = reqwest::Client::new();
        let release_url = format!("{}/repos/Drakkar-Software/OctoBot/releases/latest", server.uri());
        let release: GithubRelease = client.get(&release_url).send().await.unwrap().json().await.unwrap();
        let asset_name = platform_asset_name().unwrap();
        let result = release.assets.iter().find(|a| a.name == asset_name);
        assert!(result.is_none());
    }
}
