pub mod error;
pub mod github;
pub mod manifest;
pub mod restart;
pub mod updater;

pub use error::{Result, UpdateError};
pub use github::fetch_latest_octobot_binary;
pub use manifest::{Artifact, ArtifactSet, Channel, Manifest, PythonArtifact};
pub use restart::RestartAttempts;
pub use updater::{AppliedUpdate, ArtifactKind, UpdateAvailability, Updater, UpdaterConfig};

pub const BAKED_PUBKEY_HEX: &str = env!("LAUNCHER_UPDATE_PUBKEY_HEX");

#[cfg(test)]
mod tests {
    mod pubkey {
        use crate::BAKED_PUBKEY_HEX;

        #[test]
        fn baked_into_binary() {
            assert!(!BAKED_PUBKEY_HEX.is_empty());
        }
    }
}
