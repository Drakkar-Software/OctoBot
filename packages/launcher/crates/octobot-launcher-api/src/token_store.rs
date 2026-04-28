use std::path::{Path, PathBuf};
use std::sync::Arc;

use argon2::{Argon2, PasswordHash, PasswordHasher, PasswordVerifier};
use base64::Engine as _;
use chrono::{DateTime, Utc};
use parking_lot::RwLock;
use rand::RngCore;
use serde::{Deserialize, Serialize};

use crate::scopes::{
    SCOPE_INSTANCES_READ, SCOPE_INSTANCES_WRITE, SCOPE_UPDATES_READ, SCOPE_WILDCARD,
};

pub const TOKEN_PREFIX: &str = "oblch_";

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TokenRecord {
    pub id: String,
    pub label: String,
    pub argon2_hash: String,
    pub scopes: Vec<String>,
    pub created_at: DateTime<Utc>,
    pub last_used_at: Option<DateTime<Utc>>,
    pub expires_at: Option<DateTime<Utc>>,
    pub revoked: bool,
}

#[derive(Debug)]
pub struct TokenStore {
    tokens: RwLock<Vec<TokenRecord>>,
    path: PathBuf,
}

impl TokenStore {
    pub fn load(path: PathBuf) -> Self {
        let tokens = Self::load_from_file(&path).unwrap_or_default();
        Self {
            tokens: RwLock::new(tokens),
            path,
        }
    }

    fn load_from_file(path: &Path) -> Option<Vec<TokenRecord>> {
        let content = std::fs::read_to_string(path).ok()?;
        serde_json::from_str(&content).ok()
    }

    pub fn verify(&self, raw_token: &str) -> Option<TokenRecord> {
        if !raw_token.starts_with(TOKEN_PREFIX) {
            return None;
        }

        let now = Utc::now();
        let tokens = self.tokens.read();

        for record in tokens.iter() {
            if record.revoked {
                continue;
            }
            if let Some(expires_at) = record.expires_at {
                if now > expires_at {
                    continue;
                }
            }

            let Ok(parsed) = PasswordHash::new(&record.argon2_hash) else {
                continue;
            };
            let argon2 = build_argon2();
            if argon2
                .verify_password(raw_token.as_bytes(), &parsed)
                .is_ok()
            {
                return Some(record.clone());
            }
        }

        None
    }

    pub fn create(
        &self,
        label: String,
        scopes: Vec<String>,
        expires_at: Option<DateTime<Utc>>,
    ) -> std::io::Result<(TokenRecord, String)> {
        let raw_token = generate_raw_token();
        let id = generate_token_id();
        let argon2_hash = hash_token(&raw_token);

        let record = TokenRecord {
            id,
            label,
            argon2_hash,
            scopes,
            created_at: Utc::now(),
            last_used_at: None,
            expires_at,
            revoked: false,
        };

        self.tokens.write().push(record.clone());
        self.save()?;

        Ok((record, raw_token))
    }

    pub fn revoke(&self, id: &str) -> std::io::Result<bool> {
        let mut tokens = self.tokens.write();
        if let Some(record) = tokens.iter_mut().find(|r| r.id == id) {
            record.revoked = true;
            drop(tokens);
            self.save()?;
            return Ok(true);
        }
        Ok(false)
    }

    pub fn list(&self) -> Vec<TokenRecord> {
        self.tokens.read().clone()
    }

    pub fn save(&self) -> std::io::Result<()> {
        let tokens = self.tokens.read();
        let content = serde_json::to_string_pretty(&*tokens)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))?;

        if let Some(parent) = self.path.parent() {
            std::fs::create_dir_all(parent)?;
        }

        let tmp_path = self.path.with_extension("tmp");

        #[cfg(unix)]
        {
            use std::io::Write;
            use std::os::unix::fs::OpenOptionsExt;
            let mut file = std::fs::OpenOptions::new()
                .write(true)
                .create(true)
                .truncate(true)
                .mode(0o600)
                .open(&tmp_path)?;
            file.write_all(content.as_bytes())?;
        }
        #[cfg(not(unix))]
        {
            std::fs::write(&tmp_path, content.as_bytes())?;
        }

        std::fs::rename(&tmp_path, &self.path)?;

        Ok(())
    }

    pub fn reload(&self) {
        if let Some(loaded) = Self::load_from_file(&self.path) {
            *self.tokens.write() = loaded;
        }
    }

    pub fn update_last_used(&self, id: &str) {
        let mut tokens = self.tokens.write();
        if let Some(record) = tokens.iter_mut().find(|r| r.id == id) {
            record.last_used_at = Some(Utc::now());
        }
        drop(tokens);
        let _ = self.save();
    }

    pub fn bootstrap_if_empty(&self) -> std::io::Result<Option<String>> {
        if !self.tokens.read().is_empty() {
            return Ok(None);
        }

        let (_, raw) = self.create(
            "admin".to_string(),
            vec![SCOPE_WILDCARD.to_string()],
            None,
        )?;

        Ok(Some(raw))
    }
}

fn generate_raw_token() -> String {
    let mut bytes = [0u8; 32];
    rand::rngs::OsRng.fill_bytes(&mut bytes);
    format!(
        "{}{}",
        TOKEN_PREFIX,
        base64::engine::general_purpose::URL_SAFE_NO_PAD.encode(bytes)
    )
}

fn generate_token_id() -> String {
    let mut bytes = [0u8; 4];
    rand::rngs::OsRng.fill_bytes(&mut bytes);
    format!("tok_{}", hex::encode(bytes))
}

fn build_argon2() -> Argon2<'static> {
    let params = argon2::Params::new(19456, 2, 1, None)
        .unwrap_or_else(|_| argon2::Params::default());
    Argon2::new(argon2::Algorithm::Argon2id, argon2::Version::V0x13, params)
}

fn hash_token(raw: &str) -> String {
    use argon2::password_hash::SaltString;
    let salt = SaltString::generate(&mut rand::rngs::OsRng);
    let argon2 = build_argon2();
    argon2
        .hash_password(raw.as_bytes(), &salt)
        .map(|h| h.to_string())
        .unwrap_or_default()
}

pub fn default_scopes() -> Vec<String> {
    vec![
        SCOPE_INSTANCES_READ.to_string(),
        SCOPE_INSTANCES_WRITE.to_string(),
        SCOPE_UPDATES_READ.to_string(),
    ]
}

pub fn token_has_scope(record: &TokenRecord, required: &str) -> bool {
    record.scopes.iter().any(|s| s == SCOPE_WILDCARD || s == required)
}

pub fn make_token_store_arc(path: PathBuf) -> Arc<TokenStore> {
    Arc::new(TokenStore::load(path))
}

#[cfg(test)]
mod tests {
    #![allow(clippy::unwrap_used, clippy::expect_used)]
    use super::*;
    use tempfile::TempDir;

    fn temp_store() -> (TokenStore, TempDir) {
        let dir = TempDir::new().expect("tempdir");
        let path = dir.path().join("tokens.json");
        (TokenStore::load(path), dir)
    }

    #[test]
    fn create_and_verify() {
        let (store, _dir) = temp_store();
        let (record, raw) = store.create("test".into(), default_scopes(), None).unwrap();
        let verified = store.verify(&raw);
        assert!(verified.is_some());
        assert_eq!(verified.unwrap().id, record.id);
    }

    #[test]
    fn revoke_rejects_token() {
        let (store, _dir) = temp_store();
        let (record, raw) = store.create("test".into(), default_scopes(), None).unwrap();
        store.revoke(&record.id).unwrap();
        assert!(store.verify(&raw).is_none());
    }

    #[test]
    fn expired_token_rejected() {
        let (store, _dir) = temp_store();
        let past = Utc::now() - chrono::Duration::seconds(1);
        let (_, raw) = store.create("test".into(), default_scopes(), Some(past)).unwrap();
        assert!(store.verify(&raw).is_none());
    }

    #[test]
    fn bootstrap_creates_wildcard_token() {
        let (store, _dir) = temp_store();
        let raw = store.bootstrap_if_empty().unwrap();
        assert!(raw.is_some());
        let raw = raw.unwrap();
        let record = store.verify(&raw).expect("should verify");
        assert!(record.scopes.contains(&SCOPE_WILDCARD.to_string()));
    }

    #[test]
    fn bootstrap_does_nothing_if_not_empty() {
        let (store, _dir) = temp_store();
        store.create("existing".into(), default_scopes(), None).unwrap();
        let raw = store.bootstrap_if_empty().unwrap();
        assert!(raw.is_none());
    }

    #[test]
    fn wrong_prefix_returns_none() {
        let (store, _dir) = temp_store();
        store.create("test".into(), default_scopes(), None).unwrap();
        assert!(store.verify("wrongprefix_abc").is_none());
    }

    #[test]
    fn token_id_format() {
        let (store, _dir) = temp_store();
        let (record, _) = store.create("test".into(), default_scopes(), None).unwrap();
        assert!(record.id.starts_with("tok_"));
        assert_eq!(record.id.len(), 4 + 8); // "tok_" + 4 hex bytes = 12 chars
    }

    #[test]
    fn raw_token_format() {
        let (store, _dir) = temp_store();
        let (_, raw) = store.create("test".into(), default_scopes(), None).unwrap();
        assert!(raw.starts_with(TOKEN_PREFIX));
        assert!(raw.len() > 40);
    }
}
