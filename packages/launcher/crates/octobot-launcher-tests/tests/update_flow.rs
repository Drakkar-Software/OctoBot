#![allow(clippy::unwrap_used, clippy::expect_used)]

use std::collections::BTreeMap;

use ed25519_dalek::{Signer, SigningKey};
use octobot_launcher_update::{
    UpdateAvailability, UpdateError, Updater, UpdaterConfig,
    manifest::{Artifact, ArtifactSet, Channel, Manifest},
};
use rand::rngs::OsRng;
use sha2::{Digest, Sha256};
use wiremock::matchers::{method, path};
use wiremock::{Mock, MockServer, ResponseTemplate};

const TRIPLE: &str = "x86_64-unknown-linux-gnu";

fn make_manifest(version: &str) -> Manifest {
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

fn sign_manifest(key: &SigningKey, manifest_bytes: &[u8]) -> String {
    let hash = Sha256::digest(manifest_bytes);
    let sig = key.sign(&hash);
    hex::encode(sig.to_bytes())
}

fn make_config(server: &MockServer, key: &SigningKey, current_version: &str) -> UpdaterConfig {
    UpdaterConfig {
        manifest_url: format!("{}/manifest.json", server.uri()),
        channel: "stable".to_string(),
        current_launcher_version: semver::Version::parse(current_version).unwrap(),
        current_target_triple: TRIPLE,
        pubkey: key.verifying_key(),
        allow_downgrade: false,
        user_agent: "test".to_string(),
        state_dir: std::env::temp_dir(),
        cache_dir: std::env::temp_dir(),
    }
}

async fn mount(server: &MockServer, manifest: &Manifest, key: &SigningKey) {
    let body = serde_json::to_vec(manifest).unwrap();
    let sig = sign_manifest(key, &body);
    Mock::given(method("GET"))
        .and(path("/manifest.json"))
        .respond_with(ResponseTemplate::new(200).set_body_bytes(body))
        .mount(server)
        .await;
    Mock::given(method("GET"))
        .and(path("/manifest.json.sig"))
        .respond_with(ResponseTemplate::new(200).set_body_string(sig))
        .mount(server)
        .await;
}

#[tokio::test]
async fn happy_path_update_check() {
    let server = MockServer::start().await;
    let key = SigningKey::generate(&mut OsRng);
    let manifest = make_manifest("2.0.0");
    mount(&server, &manifest, &key).await;

    let updater = Updater::new(make_config(&server, &key, "1.0.0"));
    let result = updater.check_launcher().await.unwrap();
    assert_eq!(result, UpdateAvailability::Available { version: "2.0.0".to_string() });
}

#[tokio::test]
async fn bad_signature_rejected() {
    let server = MockServer::start().await;
    let signing_key = SigningKey::generate(&mut OsRng);
    let wrong_key = SigningKey::generate(&mut OsRng);

    let manifest = make_manifest("2.0.0");
    let body = serde_json::to_vec(&manifest).unwrap();
    let bad_sig = sign_manifest(&wrong_key, &body);

    Mock::given(method("GET"))
        .and(path("/manifest.json"))
        .respond_with(ResponseTemplate::new(200).set_body_bytes(body))
        .mount(&server)
        .await;
    Mock::given(method("GET"))
        .and(path("/manifest.json.sig"))
        .respond_with(ResponseTemplate::new(200).set_body_string(bad_sig))
        .mount(&server)
        .await;

    let updater = Updater::new(make_config(&server, &signing_key, "1.0.0"));
    let result = updater.check_launcher().await;
    assert!(matches!(result, Err(UpdateError::BadSignature)));
}

#[tokio::test]
async fn missing_artifact_for_triple() {
    let server = MockServer::start().await;
    let key = SigningKey::generate(&mut OsRng);

    let mut channels = BTreeMap::new();
    channels.insert(
        "stable".to_string(),
        Channel {
            launcher: Some(ArtifactSet {
                version: "2.0.0".to_string(),
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
    mount(&server, &manifest, &key).await;

    let updater = Updater::new(make_config(&server, &key, "1.0.0"));
    let result = updater.check_launcher().await.unwrap();
    assert_eq!(result, UpdateAvailability::NoArtifactForPlatform);
}

#[tokio::test]
async fn downgrade_blocked_by_default() {
    let server = MockServer::start().await;
    let key = SigningKey::generate(&mut OsRng);
    let manifest = make_manifest("1.0.0");
    mount(&server, &manifest, &key).await;

    let updater = Updater::new(make_config(&server, &key, "2.0.0"));
    let result = updater.check_launcher().await.unwrap();
    assert_eq!(result, UpdateAvailability::UpToDate);
}

#[tokio::test]
async fn network_failure_mid_download() {
    let server = MockServer::start().await;
    let key = SigningKey::generate(&mut OsRng);

    Mock::given(method("GET"))
        .and(path("/manifest.json"))
        .respond_with(ResponseTemplate::new(500))
        .mount(&server)
        .await;

    let updater = Updater::new(make_config(&server, &key, "1.0.0"));
    let result = updater.check_launcher().await;
    assert!(result.is_err());
}
