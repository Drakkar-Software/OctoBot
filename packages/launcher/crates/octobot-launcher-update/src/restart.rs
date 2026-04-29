use std::path::Path;

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};

#[derive(Debug, Default, Serialize, Deserialize)]
pub struct RestartAttempts {
    pub count: u32,
    pub last_reset: Option<DateTime<Utc>>,
}

impl RestartAttempts {
    pub fn load(state_dir: &Path) -> Self {
        let path = state_dir.join("restart_attempts.json");
        let Ok(data) = std::fs::read(&path) else {
            return Self::default();
        };
        serde_json::from_slice(&data).unwrap_or_default()
    }

    pub fn save(&self, state_dir: &Path) -> std::io::Result<()> {
        let path = state_dir.join("restart_attempts.json");
        let data = serde_json::to_vec(self)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::InvalidData, e))?;
        std::fs::write(path, data)
    }

    pub fn increment(&mut self) {
        self.count += 1;
    }

    pub fn reset(&mut self) {
        self.count = 0;
        self.last_reset = Some(Utc::now());
    }

    pub fn should_rollback(&self) -> bool {
        self.count >= 3
    }
}

#[cfg(test)]
mod tests {
    mod rollback {
        use crate::restart::RestartAttempts;

        #[test]
        fn three_failures_triggers_rollback() {
            let mut attempts = RestartAttempts::default();
            attempts.increment();
            attempts.increment();
            attempts.increment();
            assert!(attempts.should_rollback());
        }

        #[test]
        fn counter_resets_on_clean_run() {
            let mut attempts = RestartAttempts::default();
            attempts.increment();
            attempts.increment();
            attempts.reset();
            assert_eq!(attempts.count, 0);
            assert!(!attempts.should_rollback());
        }
    }
}
