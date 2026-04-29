use std::collections::BTreeMap;

use chrono::{DateTime, Utc};
use ed25519_dalek::Signature;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use crate::error::{Result, UpdateError};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Manifest {
    pub schema_version: u32,
    pub generated_at: DateTime<Utc>,
    pub channels: BTreeMap<String, Channel>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Channel {
    pub launcher: Option<ArtifactSet>,
    pub octobot_binary: Option<ArtifactSet>,
    pub octobot_python: Option<PythonArtifact>,
    pub python_dist: Option<ArtifactSet>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ArtifactSet {
    pub version: String,
    pub artifacts: BTreeMap<String, Artifact>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Artifact {
    pub url: String,
    pub sha256: String,
    pub size: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PythonArtifact {
    pub version: String,
    pub pypi_index: String,
    pub package: String,
}

pub fn canonical_bytes(manifest: &Manifest) -> Result<Vec<u8>> {
    serde_json::to_vec(manifest).map_err(|e| UpdateError::Parse(e.to_string()))
}

pub fn verify_signature(
    body: &[u8],
    sig_hex: &str,
    pubkey: &ed25519_dalek::VerifyingKey,
) -> Result<()> {
    let sig_bytes = hex::decode(sig_hex.trim()).map_err(|_| UpdateError::MalformedSignature)?;
    let sig_arr: [u8; 64] = sig_bytes
        .try_into()
        .map_err(|_| UpdateError::MalformedSignature)?;
    let signature = Signature::from_bytes(&sig_arr);
    let hash = Sha256::digest(body);
    pubkey
        .verify_strict(&hash, &signature)
        .map_err(|_| UpdateError::BadSignature)
}

pub fn parse_and_verify(
    body: &[u8],
    sig_hex: &str,
    pubkey: &ed25519_dalek::VerifyingKey,
) -> Result<Manifest> {
    verify_signature(body, sig_hex, pubkey)?;
    serde_json::from_slice(body).map_err(|e| UpdateError::Parse(e.to_string()))
}

#[cfg(test)]
#[allow(clippy::unwrap_used, clippy::expect_used, clippy::missing_panics_doc)]
mod tests {
    use super::*;
    use ed25519_dalek::{Signer, SigningKey};
    use sha2::{Digest, Sha256};
    use wiremock::matchers::{method, path};
    use wiremock::{Mock, MockServer, ResponseTemplate};

    fn make_manifest() -> Manifest {
        let mut channels = BTreeMap::new();
        let mut artifacts = BTreeMap::new();
        artifacts.insert(
            "x86_64-unknown-linux-gnu".to_string(),
            Artifact {
                url: "https://example.com/launcher".to_string(),
                sha256: "abc123".to_string(),
                size: 1_000_000,
            },
        );
        channels.insert(
            "stable".to_string(),
            Channel {
                launcher: Some(ArtifactSet {
                    version: "1.4.2".to_string(),
                    artifacts,
                }),
                octobot_binary: None,
                octobot_python: None,
                python_dist: None,
            },
        );
        Manifest {
            schema_version: 1,
            generated_at: chrono::DateTime::parse_from_rfc3339("2026-04-27T10:30:00Z")
                .unwrap()
                .with_timezone(&Utc),
            channels,
        }
    }

    fn sign_manifest(manifest: &Manifest, key: &SigningKey) -> String {
        let body = serde_json::to_vec(manifest).unwrap();
        let hash = Sha256::digest(&body);
        let sig = key.sign(&hash);
        hex::encode(sig.to_bytes())
    }

    #[test]
    fn canonical_json_is_deterministic() {
        let manifest = make_manifest();
        let bytes1 = serde_json::to_vec(&manifest).unwrap();
        let bytes2 = serde_json::to_vec(&manifest).unwrap();
        assert_eq!(bytes1, bytes2);
    }

    #[test]
    fn signature_verifies_with_correct_key() {
        let key = SigningKey::generate(&mut rand::rngs::OsRng);
        let manifest = make_manifest();
        let sig_hex = sign_manifest(&manifest, &key);
        let body = serde_json::to_vec(&manifest).unwrap();
        let result = verify_signature(&body, &sig_hex, &key.verifying_key());
        assert!(result.is_ok());
    }

    #[test]
    fn signature_fails_with_wrong_key() {
        let key_a = SigningKey::generate(&mut rand::rngs::OsRng);
        let key_b = SigningKey::generate(&mut rand::rngs::OsRng);
        let manifest = make_manifest();
        let sig_hex = sign_manifest(&manifest, &key_a);
        let body = serde_json::to_vec(&manifest).unwrap();
        let result = verify_signature(&body, &sig_hex, &key_b.verifying_key());
        assert!(matches!(result, Err(UpdateError::BadSignature)));
    }

    #[test]
    fn tampered_manifest_fails() {
        let key = SigningKey::generate(&mut rand::rngs::OsRng);
        let manifest = make_manifest();
        let sig_hex = sign_manifest(&manifest, &key);
        let mut body = serde_json::to_vec(&manifest).unwrap();
        body[10] ^= 0xFF;
        let result = verify_signature(&body, &sig_hex, &key.verifying_key());
        assert!(matches!(result, Err(UpdateError::BadSignature)));
    }

    #[tokio::test]
    async fn missing_sig_file_fails() {
        use crate::updater::{Updater, UpdaterConfig};

        let server = MockServer::start().await;
        let key = SigningKey::generate(&mut rand::rngs::OsRng);
        let manifest = make_manifest();
        let body = serde_json::to_vec(&manifest).unwrap();

        Mock::given(method("GET"))
            .and(path("/manifest.json"))
            .respond_with(ResponseTemplate::new(200).set_body_bytes(body))
            .mount(&server)
            .await;

        Mock::given(method("GET"))
            .and(path("/manifest.json.sig"))
            .respond_with(ResponseTemplate::new(404))
            .mount(&server)
            .await;

        let config = UpdaterConfig {
            manifest_url: format!("{}/manifest.json", server.uri()),
            channel: "stable".to_string(),
            current_launcher_version: semver::Version::new(1, 0, 0),
            current_target_triple: "x86_64-unknown-linux-gnu",
            pubkey: key.verifying_key(),
            allow_downgrade: false,
            user_agent: "test".to_string(),
            state_dir: std::env::temp_dir(),
            cache_dir: std::env::temp_dir(),
        };
        let updater = Updater::new(config);
        let result = updater.fetch_manifest().await;
        assert!(matches!(result, Err(UpdateError::MissingSignature)));
    }

    #[test]
    fn malformed_sig_fails() {
        let key = SigningKey::generate(&mut rand::rngs::OsRng);
        let manifest = make_manifest();
        let body = serde_json::to_vec(&manifest).unwrap();
        let result = verify_signature(&body, "not-hex", &key.verifying_key());
        assert!(matches!(result, Err(UpdateError::MalformedSignature)));
    }
}
