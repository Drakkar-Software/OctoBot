use std::path::{Path, PathBuf};

use ed25519_dalek::VerifyingKey;
use semver::Version;
use sha2::{Digest, Sha256};
use tracing::{debug, info};

use crate::error::{Result, UpdateError};
use crate::manifest::{ArtifactSet, Manifest};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum UpdateAvailability {
    UpToDate,
    Available { version: String },
    NoArtifactForPlatform,
}

#[derive(Debug, Clone)]
pub enum ArtifactKind {
    OctoBotBinary,
    PythonDist,
}

#[derive(Debug)]
pub struct AppliedUpdate {
    pub version: String,
}

#[derive(Debug)]
pub struct UpdaterConfig {
    pub manifest_url: String,
    pub channel: String,
    pub current_launcher_version: Version,
    pub current_target_triple: &'static str,
    pub pubkey: VerifyingKey,
    pub allow_downgrade: bool,
    pub user_agent: String,
    pub state_dir: PathBuf,
    pub cache_dir: PathBuf,
}

type Replacer = Box<dyn Fn(&Path) -> std::io::Result<()> + Send + Sync>;

pub struct Updater {
    config: UpdaterConfig,
    client: reqwest::Client,
    replacer: Replacer,
}

impl std::fmt::Debug for Updater {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("Updater")
            .field("config", &self.config)
            .finish_non_exhaustive()
    }
}

impl Updater {
    pub fn new(config: UpdaterConfig) -> Self {
        let client = reqwest::Client::builder()
            .user_agent(&config.user_agent)
            .build()
            .unwrap_or_else(|_| reqwest::Client::new());
        Self {
            config,
            client,
            replacer: Box::new(|path| self_replace::self_replace(path)),
        }
    }

    /// Build an `Updater` from the baked-in public key hex and config strings.
    /// Returns `None` if the pubkey cannot be parsed (e.g. dev builds with all-zero placeholder).
    pub fn from_baked_config(
        manifest_url: String,
        channel: String,
        pubkey_hex: &str,
        state_dir: PathBuf,
        cache_dir: PathBuf,
    ) -> Option<Self> {
        let bytes = hex::decode(pubkey_hex).ok()?;
        let arr: [u8; 32] = bytes.try_into().ok()?;
        // Reject the dev placeholder (all zeros) — not a real key.
        if arr == [0u8; 32] {
            return None;
        }
        let pubkey = VerifyingKey::from_bytes(&arr).ok()?;
        let version = Version::parse(env!("CARGO_PKG_VERSION")).ok()?;
        let config = UpdaterConfig {
            manifest_url,
            channel,
            current_launcher_version: version,
            current_target_triple: env!("LAUNCHER_TARGET_TRIPLE"),
            pubkey,
            allow_downgrade: false,
            user_agent: format!("octobot-launcher/{}", env!("CARGO_PKG_VERSION")),
            state_dir,
            cache_dir,
        };
        Some(Self::new(config))
    }

    #[cfg(test)]
    pub fn with_replacer(mut self, replacer: Replacer) -> Self {
        self.replacer = replacer;
        self
    }

    pub async fn fetch_manifest(&self) -> Result<Manifest> {
        let body_bytes = self.get_bytes(&self.config.manifest_url).await?;
        let sig_url = format!("{}.sig", self.config.manifest_url);
        let sig_resp = self
            .client
            .get(&sig_url)
            .send()
            .await
            .map_err(|e| UpdateError::Network(e.to_string()))?;
        if sig_resp.status().as_u16() == 404 {
            return Err(UpdateError::MissingSignature);
        }
        if !sig_resp.status().is_success() {
            return Err(UpdateError::Network(format!(
                "sig fetch status {}",
                sig_resp.status()
            )));
        }
        let sig_hex = sig_resp
            .text()
            .await
            .map_err(|e| UpdateError::Network(e.to_string()))?;
        crate::manifest::parse_and_verify(&body_bytes, &sig_hex, &self.config.pubkey)
    }

    pub async fn check_launcher(&self) -> Result<UpdateAvailability> {
        let manifest = self.fetch_manifest().await?;
        let channel = manifest
            .channels
            .get(&self.config.channel)
            .ok_or_else(|| UpdateError::Parse(format!("channel not found: {}", self.config.channel)))?;
        let Some(launcher_set) = &channel.launcher else {
            return Ok(UpdateAvailability::UpToDate);
        };
        if !launcher_set
            .artifacts
            .contains_key(self.config.current_target_triple)
        {
            return Ok(UpdateAvailability::NoArtifactForPlatform);
        }
        self.compare_versions(&self.config.current_launcher_version, launcher_set)
    }

    pub async fn check_artifact(&self, artifact: ArtifactKind) -> Result<UpdateAvailability> {
        let manifest = self.fetch_manifest().await?;
        let channel = manifest
            .channels
            .get(&self.config.channel)
            .ok_or_else(|| UpdateError::Parse(format!("channel not found: {}", self.config.channel)))?;
        let set = match artifact {
            ArtifactKind::OctoBotBinary => match &channel.octobot_binary {
                Some(s) => s,
                None => return Ok(UpdateAvailability::UpToDate),
            },
            ArtifactKind::PythonDist => match &channel.python_dist {
                Some(s) => s,
                None => return Ok(UpdateAvailability::UpToDate),
            },
        };
        if !set
            .artifacts
            .contains_key(self.config.current_target_triple)
        {
            return Ok(UpdateAvailability::NoArtifactForPlatform);
        }
        let current = Version::new(0, 0, 0);
        self.compare_versions(&current, set)
    }

    pub async fn apply_launcher_update(&self, manifest: &Manifest) -> Result<AppliedUpdate> {
        let lock_path = self.config.state_dir.join("launcher.lock");
        if lock_path.exists() {
            return Err(UpdateError::Locked);
        }

        let channel = manifest
            .channels
            .get(&self.config.channel)
            .ok_or_else(|| UpdateError::Parse(format!("channel not found: {}", self.config.channel)))?;
        let launcher_set = channel
            .launcher
            .as_ref()
            .ok_or_else(|| UpdateError::Parse("no launcher in channel".to_string()))?;
        let artifact = launcher_set
            .artifacts
            .get(self.config.current_target_triple)
            .ok_or_else(|| {
                UpdateError::NoArtifactForPlatform(self.config.current_target_triple.to_string())
            })?;

        let updates_dir = self.config.cache_dir.join("updates");
        std::fs::create_dir_all(&updates_dir)?;

        let partial_name = format!(
            "octobot-launcher.{}.partial",
            launcher_set.version
        );
        let partial_path = updates_dir.join(&partial_name);

        self.download_and_verify(&artifact.url, &artifact.sha256, &partial_path)
            .await?;

        let backup_name = format!(
            "octobot-launcher.{}",
            self.config.current_launcher_version
        );
        let backup_path = updates_dir.join(&backup_name);
        let current_exe =
            std::env::current_exe().map_err(UpdateError::Io)?;
        std::fs::copy(&current_exe, &backup_path)?;
        debug!("backup created at {}", backup_path.display());

        (self.replacer)(&partial_path)?;
        info!("launcher replaced with version {}", launcher_set.version);

        let pending_restart = self.config.state_dir.join("pending_restart");
        std::fs::write(&pending_restart, launcher_set.version.as_bytes())?;

        Ok(AppliedUpdate {
            version: launcher_set.version.clone(),
        })
    }

    pub async fn fetch_artifact(
        &self,
        kind: ArtifactKind,
        dest_dir: &Path,
    ) -> Result<PathBuf> {
        let manifest = self.fetch_manifest().await?;
        let channel = manifest
            .channels
            .get(&self.config.channel)
            .ok_or_else(|| UpdateError::Parse(format!("channel not found: {}", self.config.channel)))?;
        let (url, sha256) = match kind {
            ArtifactKind::OctoBotBinary => {
                let set = channel
                    .octobot_binary
                    .as_ref()
                    .ok_or_else(|| UpdateError::Parse("no octobot_binary in channel".to_string()))?;
                let artifact = set
                    .artifacts
                    .get(self.config.current_target_triple)
                    .ok_or_else(|| {
                        UpdateError::NoArtifactForPlatform(
                            self.config.current_target_triple.to_string(),
                        )
                    })?;
                (artifact.url.clone(), artifact.sha256.clone())
            }
            ArtifactKind::PythonDist => {
                let set = channel
                    .python_dist
                    .as_ref()
                    .ok_or_else(|| UpdateError::Parse("no python_dist in channel".to_string()))?;
                let artifact = set
                    .artifacts
                    .get(self.config.current_target_triple)
                    .ok_or_else(|| {
                        UpdateError::NoArtifactForPlatform(
                            self.config.current_target_triple.to_string(),
                        )
                    })?;
                (artifact.url.clone(), artifact.sha256.clone())
            }
        };

        let filename = url
            .rsplit('/')
            .next()
            .unwrap_or("artifact")
            .to_string();
        let partial_path = dest_dir.join(format!("{filename}.partial"));
        self.download_and_verify(&url, &sha256, &partial_path).await?;
        let final_path = dest_dir.join(&filename);
        std::fs::rename(&partial_path, &final_path)?;
        Ok(final_path)
    }

    async fn get_bytes(&self, url: &str) -> Result<Vec<u8>> {
        let resp = self
            .client
            .get(url)
            .send()
            .await
            .map_err(|e| UpdateError::Network(e.to_string()))?;
        if !resp.status().is_success() {
            return Err(UpdateError::Network(format!(
                "HTTP {} for {url}",
                resp.status()
            )));
        }
        resp.bytes()
            .await
            .map(|b| b.to_vec())
            .map_err(|e| UpdateError::Network(e.to_string()))
    }

    async fn download_and_verify(
        &self,
        url: &str,
        expected_sha256: &str,
        dest: &Path,
    ) -> Result<()> {
        let bytes = self.get_bytes(url).await?;
        let hash = Sha256::digest(&bytes);
        let actual_hex = hex::encode(hash);
        if actual_hex != expected_sha256 {
            return Err(UpdateError::Sha256Mismatch);
        }
        if let Some(parent) = dest.parent() {
            std::fs::create_dir_all(parent)?;
        }
        std::fs::write(dest, &bytes)?;
        Ok(())
    }

    fn compare_versions(
        &self,
        current: &Version,
        set: &ArtifactSet,
    ) -> Result<UpdateAvailability> {
        let manifest_version = Version::parse(&set.version)
            .map_err(|e| UpdateError::Parse(format!("bad version {}: {e}", set.version)))?;
        if manifest_version == *current {
            return Ok(UpdateAvailability::UpToDate);
        }
        if manifest_version > *current {
            return Ok(UpdateAvailability::Available {
                version: set.version.clone(),
            });
        }
        if self.config.allow_downgrade {
            return Ok(UpdateAvailability::Available {
                version: set.version.clone(),
            });
        }
        Ok(UpdateAvailability::UpToDate)
    }
}

#[cfg(test)]
mod tests {
    use std::collections::BTreeMap;

    use ed25519_dalek::{Signer, SigningKey};
    use sha2::{Digest, Sha256};
    use wiremock::matchers::{method, path};
    use wiremock::{Mock, MockServer, ResponseTemplate};

    use super::*;
    use crate::manifest::{Artifact, ArtifactSet, Channel, Manifest};

    const TRIPLE: &str = "x86_64-unknown-linux-gnu";

    fn make_manifest_with_launcher_version(version: &str) -> Manifest {
        let mut artifacts = BTreeMap::new();
        artifacts.insert(
            TRIPLE.to_string(),
            Artifact {
                url: "https://example.com/launcher".to_string(),
                sha256: "deadbeef".to_string(),
                size: 1_000_000,
            },
        );
        let mut channels = BTreeMap::new();
        channels.insert(
            "stable".to_string(),
            Channel {
                launcher: Some(ArtifactSet {
                    version: version.to_string(),
                    artifacts,
                }),
                octobot_binary: None,
                octobot_python: None,
                python_dist: None,
            },
        );
        Manifest {
            schema_version: 1,
            generated_at: chrono::Utc::now(),
            channels,
        }
    }

    fn sign_and_serve_manifest(
        manifest: &Manifest,
        key: &SigningKey,
    ) -> (Vec<u8>, String) {
        #[allow(clippy::unwrap_used)]
        let body = serde_json::to_vec(manifest).unwrap();
        let hash = Sha256::digest(&body);
        let sig = key.sign(&hash);
        let sig_hex = hex::encode(sig.to_bytes());
        (body, sig_hex)
    }

    #[allow(clippy::unwrap_used)]
    fn make_updater_config(
        server: &MockServer,
        key: &SigningKey,
        current_version: &str,
        allow_downgrade: bool,
    ) -> UpdaterConfig {
        UpdaterConfig {
            manifest_url: format!("{}/manifest.json", server.uri()),
            channel: "stable".to_string(),
            current_launcher_version: Version::parse(current_version).unwrap(),
            current_target_triple: TRIPLE,
            pubkey: key.verifying_key(),
            allow_downgrade,
            user_agent: "test".to_string(),
            state_dir: std::env::temp_dir(),
            cache_dir: std::env::temp_dir(),
        }
    }

    async fn mount_manifest(server: &MockServer, manifest: &Manifest, key: &SigningKey) {
        let (body, sig_hex) = sign_and_serve_manifest(manifest, key);
        Mock::given(method("GET"))
            .and(path("/manifest.json"))
            .respond_with(ResponseTemplate::new(200).set_body_bytes(body))
            .mount(server)
            .await;
        Mock::given(method("GET"))
            .and(path("/manifest.json.sig"))
            .respond_with(ResponseTemplate::new(200).set_body_string(sig_hex))
            .mount(server)
            .await;
    }

    #[allow(clippy::unwrap_used, clippy::expect_used, clippy::missing_panics_doc)]
    mod check {
        use super::*;

        #[tokio::test]
        async fn up_to_date_returns_uptodate() {
            let server = MockServer::start().await;
            let key = SigningKey::generate(&mut rand::rngs::OsRng);
            let manifest = make_manifest_with_launcher_version("1.4.0");
            mount_manifest(&server, &manifest, &key).await;
            let updater = Updater::new(make_updater_config(&server, &key, "1.4.0", false));
            let result = updater.check_launcher().await.unwrap();
            assert_eq!(result, UpdateAvailability::UpToDate);
        }

        #[tokio::test]
        async fn newer_returns_available() {
            let server = MockServer::start().await;
            let key = SigningKey::generate(&mut rand::rngs::OsRng);
            let manifest = make_manifest_with_launcher_version("1.5.0");
            mount_manifest(&server, &manifest, &key).await;
            let updater = Updater::new(make_updater_config(&server, &key, "1.4.0", false));
            let result = updater.check_launcher().await.unwrap();
            assert_eq!(
                result,
                UpdateAvailability::Available {
                    version: "1.5.0".to_string()
                }
            );
        }

        #[tokio::test]
        async fn older_returns_uptodate_unless_downgrade() {
            let server = MockServer::start().await;
            let key = SigningKey::generate(&mut rand::rngs::OsRng);
            let manifest = make_manifest_with_launcher_version("1.3.0");
            mount_manifest(&server, &manifest, &key).await;
            let updater = Updater::new(make_updater_config(&server, &key, "1.4.0", false));
            let result = updater.check_launcher().await.unwrap();
            assert_eq!(result, UpdateAvailability::UpToDate);

            let server2 = MockServer::start().await;
            let key2 = SigningKey::generate(&mut rand::rngs::OsRng);
            let manifest2 = make_manifest_with_launcher_version("1.3.0");
            mount_manifest(&server2, &manifest2, &key2).await;
            let updater2 = Updater::new(make_updater_config(&server2, &key2, "1.4.0", true));
            let result2 = updater2.check_launcher().await.unwrap();
            assert_eq!(
                result2,
                UpdateAvailability::Available {
                    version: "1.3.0".to_string()
                }
            );
        }

        #[tokio::test]
        async fn missing_artifact_for_triple_errors() {
            let server = MockServer::start().await;
            let key = SigningKey::generate(&mut rand::rngs::OsRng);
            let mut channels = BTreeMap::new();
            channels.insert(
                "stable".to_string(),
                Channel {
                    launcher: Some(ArtifactSet {
                        version: "1.5.0".to_string(),
                        artifacts: BTreeMap::new(),
                    }),
                    octobot_binary: None,
                    octobot_python: None,
                    python_dist: None,
                },
            );
            let manifest = Manifest {
                schema_version: 1,
                generated_at: chrono::Utc::now(),
                channels,
            };
            mount_manifest(&server, &manifest, &key).await;
            let updater = Updater::new(make_updater_config(&server, &key, "1.4.0", false));
            let result = updater.check_launcher().await.unwrap();
            assert_eq!(result, UpdateAvailability::NoArtifactForPlatform);
        }
    }

    #[allow(clippy::unwrap_used, clippy::expect_used, clippy::missing_panics_doc)]
    mod download {
        use super::*;

        #[tokio::test]
        async fn sha256_mismatch_fails() {
            let server = MockServer::start().await;
            let key = SigningKey::generate(&mut rand::rngs::OsRng);

            let file_content = b"fake binary content";
            let wrong_sha256 = "0".repeat(64);

            Mock::given(method("GET"))
                .and(path("/file.bin"))
                .respond_with(
                    ResponseTemplate::new(200).set_body_bytes(file_content.to_vec()),
                )
                .mount(&server)
                .await;

            let mut artifacts = BTreeMap::new();
            artifacts.insert(
                TRIPLE.to_string(),
                Artifact {
                    url: format!("{}/file.bin", server.uri()),
                    sha256: wrong_sha256.clone(),
                    size: file_content.len() as u64,
                },
            );
            let mut channels = BTreeMap::new();
            channels.insert(
                "stable".to_string(),
                Channel {
                    launcher: Some(ArtifactSet {
                        version: "1.5.0".to_string(),
                        artifacts,
                    }),
                    octobot_binary: None,
                    octobot_python: None,
                    python_dist: None,
                },
            );
            let manifest = Manifest {
                schema_version: 1,
                generated_at: chrono::Utc::now(),
                channels,
            };
            mount_manifest(&server, &manifest, &key).await;

            let tmp = tempfile::tempdir().unwrap();
            let config = UpdaterConfig {
                manifest_url: format!("{}/manifest.json", server.uri()),
                channel: "stable".to_string(),
                current_launcher_version: Version::parse("1.4.0").unwrap(),
                current_target_triple: TRIPLE,
                pubkey: key.verifying_key(),
                allow_downgrade: false,
                user_agent: "test".to_string(),
                state_dir: tmp.path().to_path_buf(),
                cache_dir: tmp.path().to_path_buf(),
            };
            let updater = Updater::new(config);
            let partial = tmp.path().join("file.bin.partial");
            let artifact_url = format!("{}/file.bin", server.uri());
            let result = updater
                .download_and_verify(&artifact_url, &wrong_sha256, &partial)
                .await;
            assert!(matches!(result, Err(UpdateError::Sha256Mismatch)));
        }

        #[tokio::test]
        async fn network_error_propagates() {
            let server = MockServer::start().await;
            let key = SigningKey::generate(&mut rand::rngs::OsRng);

            Mock::given(method("GET"))
                .and(path("/file.bin"))
                .respond_with(ResponseTemplate::new(500))
                .mount(&server)
                .await;

            let config = UpdaterConfig {
                manifest_url: format!("{}/manifest.json", server.uri()),
                channel: "stable".to_string(),
                current_launcher_version: Version::parse("1.4.0").unwrap(),
                current_target_triple: TRIPLE,
                pubkey: key.verifying_key(),
                allow_downgrade: false,
                user_agent: "test".to_string(),
                state_dir: std::env::temp_dir(),
                cache_dir: std::env::temp_dir(),
            };
            let updater = Updater::new(config);
            let partial = std::env::temp_dir().join("test.partial");
            let result = updater
                .download_and_verify(
                    &format!("{}/file.bin", server.uri()),
                    "deadbeef",
                    &partial,
                )
                .await;
            assert!(matches!(result, Err(UpdateError::Network(_))));
        }
    }

    #[allow(clippy::unwrap_used, clippy::expect_used, clippy::missing_panics_doc)]
    mod apply {
        use super::*;

        async fn make_apply_manifest(server: &MockServer, key: &SigningKey, content: &[u8]) -> Manifest {
            let sha256 = hex::encode(Sha256::digest(content));
            Mock::given(method("GET"))
                .and(path("/launcher.bin"))
                .respond_with(
                    ResponseTemplate::new(200).set_body_bytes(content.to_vec()),
                )
                .mount(server)
                .await;
            let mut artifacts = BTreeMap::new();
            artifacts.insert(
                TRIPLE.to_string(),
                Artifact {
                    url: format!("{}/launcher.bin", server.uri()),
                    sha256,
                    size: content.len() as u64,
                },
            );
            let mut channels = BTreeMap::new();
            channels.insert(
                "stable".to_string(),
                Channel {
                    launcher: Some(ArtifactSet {
                        version: "1.5.0".to_string(),
                        artifacts,
                    }),
                    octobot_binary: None,
                    octobot_python: None,
                    python_dist: None,
                },
            );
            let manifest = Manifest {
                schema_version: 1,
                generated_at: chrono::Utc::now(),
                channels,
            };
            mount_manifest(server, &manifest, key).await;
            manifest
        }

        #[tokio::test]
        async fn self_replace_writes_pending_restart() {
            let server = MockServer::start().await;
            let key = SigningKey::generate(&mut rand::rngs::OsRng);
            let manifest = make_apply_manifest(&server, &key, b"fake binary content").await;

            let tmp = tempfile::tempdir().unwrap();
            let state_dir = tmp.path().to_path_buf();
            let cache_dir = tmp.path().to_path_buf();

            let config = UpdaterConfig {
                manifest_url: format!("{}/manifest.json", server.uri()),
                channel: "stable".to_string(),
                current_launcher_version: Version::parse("1.4.0").unwrap(),
                current_target_triple: TRIPLE,
                pubkey: key.verifying_key(),
                allow_downgrade: false,
                user_agent: "test".to_string(),
                state_dir: state_dir.clone(),
                cache_dir: cache_dir.clone(),
            };
            let updater = Updater::new(config).with_replacer(Box::new(|_path| Ok(())));
            let result = updater.apply_launcher_update(&manifest).await.unwrap();
            assert_eq!(result.version, "1.5.0");
            assert!(state_dir.join("pending_restart").exists());
        }

        #[tokio::test]
        async fn backup_created_before_swap() {
            let server = MockServer::start().await;
            let key = SigningKey::generate(&mut rand::rngs::OsRng);
            let manifest = make_apply_manifest(&server, &key, b"fake binary content v2").await;

            let tmp = tempfile::tempdir().unwrap();
            let cache_dir = tmp.path().to_path_buf();
            let state_dir = tmp.path().to_path_buf();

            let config = UpdaterConfig {
                manifest_url: format!("{}/manifest.json", server.uri()),
                channel: "stable".to_string(),
                current_launcher_version: Version::parse("1.4.0").unwrap(),
                current_target_triple: TRIPLE,
                pubkey: key.verifying_key(),
                allow_downgrade: false,
                user_agent: "test".to_string(),
                state_dir,
                cache_dir: cache_dir.clone(),
            };
            let updater = Updater::new(config).with_replacer(Box::new(|_path| Ok(())));
            updater.apply_launcher_update(&manifest).await.unwrap();
            let backup = cache_dir.join("updates").join("octobot-launcher.1.4.0");
            assert!(backup.exists());
        }
    }

    #[allow(clippy::unwrap_used, clippy::expect_used, clippy::missing_panics_doc)]
    mod lock {
        use super::*;

        #[tokio::test]
        async fn no_apply_during_instance_restart() {
            let server = MockServer::start().await;
            let key = SigningKey::generate(&mut rand::rngs::OsRng);

            let tmp = tempfile::tempdir().unwrap();
            let state_dir = tmp.path().to_path_buf();
            std::fs::write(state_dir.join("launcher.lock"), b"locked").unwrap();

            let mut channels = BTreeMap::new();
            channels.insert(
                "stable".to_string(),
                Channel {
                    launcher: Some(ArtifactSet {
                        version: "1.5.0".to_string(),
                        artifacts: BTreeMap::new(),
                    }),
                    octobot_binary: None,
                    octobot_python: None,
                    python_dist: None,
                },
            );
            let manifest = Manifest {
                schema_version: 1,
                generated_at: chrono::Utc::now(),
                channels,
            };

            let config = UpdaterConfig {
                manifest_url: format!("{}/manifest.json", server.uri()),
                channel: "stable".to_string(),
                current_launcher_version: Version::parse("1.4.0").unwrap(),
                current_target_triple: TRIPLE,
                pubkey: key.verifying_key(),
                allow_downgrade: false,
                user_agent: "test".to_string(),
                state_dir,
                cache_dir: tmp.path().to_path_buf(),
            };
            let updater = Updater::new(config);
            let result = updater.apply_launcher_update(&manifest).await;
            assert!(matches!(result, Err(UpdateError::Locked)));
        }
    }

    mod baked_config {
        use super::*;

        #[test]
        fn all_zero_pubkey_returns_none() {
            let zeros = "0".repeat(64);
            let result = Updater::from_baked_config(
                "https://example.com/manifest.json".to_string(),
                "stable".to_string(),
                &zeros,
                std::path::PathBuf::from("/tmp"),
                std::path::PathBuf::from("/tmp"),
            );
            assert!(result.is_none(), "dev placeholder key must not produce an updater");
        }

        #[test]
        fn invalid_hex_returns_none() {
            let result = Updater::from_baked_config(
                "https://example.com/manifest.json".to_string(),
                "stable".to_string(),
                "not-valid-hex",
                std::path::PathBuf::from("/tmp"),
                std::path::PathBuf::from("/tmp"),
            );
            assert!(result.is_none());
        }

        #[test]
        fn wrong_length_hex_returns_none() {
            let result = Updater::from_baked_config(
                "https://example.com/manifest.json".to_string(),
                "stable".to_string(),
                "deadbeef",
                std::path::PathBuf::from("/tmp"),
                std::path::PathBuf::from("/tmp"),
            );
            assert!(result.is_none());
        }
    }
}
