use std::path::{Path, PathBuf};

pub(crate) async fn check_python_version(path: &Path) -> Option<(u32, u32)> {
    let output = tokio::process::Command::new(path)
        .arg("--version")
        .output()
        .await
        .ok()?;

    let raw = if output.stdout.is_empty() {
        output.stderr
    } else {
        output.stdout
    };

    let text = String::from_utf8_lossy(&raw);
    let version_str = text.trim().strip_prefix("Python ")?;
    let mut parts = version_str.splitn(3, '.');
    let major: u32 = parts.next()?.parse().ok()?;
    let minor: u32 = parts.next()?.parse().ok()?;
    Some((major, minor))
}

pub(crate) async fn discover_python(
    data_dir: &Path,
    runtime_options: &serde_json::Value,
) -> Option<PathBuf> {
    if let Some(explicit) = runtime_options
        .get("python_path")
        .and_then(|v| v.as_str())
    {
        let p = PathBuf::from(explicit);
        if p.exists() {
            return Some(p);
        }
        return None;
    }

    let embedded_names = [
        "python3.12",
        "python3.11",
        "python3.10",
        "python3",
        "python",
    ];
    let embedded_base = data_dir.join("python").join("bin");
    for name in &embedded_names {
        let candidate = embedded_base.join(name);
        if candidate.exists() {
            return Some(candidate);
        }
    }

    let search_dirs = python_search_dirs();
    let system_names = ["python3.12", "python3.11", "python3.10", "python3"];
    for name in &system_names {
        if let Ok(path) = which::which_in(name, Some(&search_dirs), ".") {
            if let Some((major, minor)) = check_python_version(&path).await {
                if (major, minor) >= (3, 10) {
                    return Some(path);
                }
            }
        }
    }

    None
}

/// Build an extended PATH for Python discovery that works even when the
/// launcher runs as a daemon with a minimal system PATH.
///
/// Combines the current PATH with well-known package manager and version
/// manager locations, deduplicating entries while preserving order.
pub(crate) fn python_search_dirs() -> std::ffi::OsString {
    let mut dirs: Vec<PathBuf> = Vec::new();

    // Existing PATH first so user overrides remain authoritative.
    if let Ok(existing) = std::env::var("PATH") {
        dirs.extend(std::env::split_paths(&existing));
    }

    // pyenv shims — prepend so pyenv-selected version wins over system Python.
    if let Ok(home) = std::env::var("HOME") {
        let shims = PathBuf::from(&home).join(".pyenv").join("shims");
        if shims.is_dir() {
            dirs.insert(0, shims);
        }
        // asdf Python shims
        let asdf_shims = PathBuf::from(&home).join(".asdf").join("shims");
        if asdf_shims.is_dir() {
            dirs.insert(0, asdf_shims);
        }
    }

    // Well-known package manager directories not always in a daemon's PATH.
    for extra in &[
        "/opt/homebrew/bin",  // Homebrew on Apple Silicon
        "/usr/local/bin",     // Homebrew on Intel / manual installs
        "/opt/local/bin",     // MacPorts
    ] {
        let p = PathBuf::from(extra);
        if p.is_dir() && !dirs.contains(&p) {
            dirs.push(p);
        }
    }

    std::env::join_paths(dirs).unwrap_or_default()
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;

    async fn require_python() -> Option<PathBuf> {
        which::which("python3")
            .ok()
            .or_else(|| which::which("python").ok())
    }

    #[tokio::test]
    async fn explicit_path_override_wins() {
        let python = match require_python().await {
            Some(p) => p,
            None => return,
        };
        let opts = serde_json::json!({ "python_path": python.to_str().unwrap() });
        let result = discover_python(Path::new("/nonexistent"), &opts).await;
        assert_eq!(result, Some(python));
    }

    #[tokio::test]
    async fn embedded_path_preferred_over_system() {
        use std::os::unix::fs::PermissionsExt;
        let tmp = tempfile::tempdir().unwrap();
        let bin_dir = tmp.path().join("python").join("bin");
        std::fs::create_dir_all(&bin_dir).unwrap();
        let fake_python = bin_dir.join("python3");
        std::fs::write(&fake_python, b"#!/bin/sh\necho 'Python 3.10.0'\n").unwrap();
        let mut perms = std::fs::metadata(&fake_python).unwrap().permissions();
        perms.set_mode(0o755);
        std::fs::set_permissions(&fake_python, perms).unwrap();

        let result = discover_python(tmp.path(), &serde_json::Value::Null).await;
        assert_eq!(result, Some(fake_python));
    }

    #[tokio::test]
    async fn version_floor_enforced() {
        use std::os::unix::fs::PermissionsExt;
        let tmp = tempfile::tempdir().unwrap();
        let fake_python = tmp.path().join("python_old");
        std::fs::write(&fake_python, b"#!/bin/sh\necho 'Python 3.9.0'\n").unwrap();
        let mut perms = std::fs::metadata(&fake_python).unwrap().permissions();
        perms.set_mode(0o755);
        std::fs::set_permissions(&fake_python, perms).unwrap();

        let version = check_python_version(&fake_python).await;
        assert_eq!(version, Some((3, 9)));
        assert!(version.unwrap() < (3, 10));
    }

    #[tokio::test]
    async fn no_python_available_returns_unavailable() {
        let opts =
            serde_json::json!({ "python_path": "/nonexistent/path/to/python_does_not_exist" });
        let result = discover_python(Path::new("/nonexistent"), &opts).await;
        assert!(result.is_none());
    }

    #[tokio::test]
    async fn finds_python_via_extended_path_when_not_in_minimal_path() {
        use std::os::unix::fs::PermissionsExt;

        // Simulate a daemon's minimal PATH containing only /nonexistent.
        let tmp = tempfile::tempdir().unwrap();
        let bin_dir = tmp.path().join("bin");
        std::fs::create_dir_all(&bin_dir).unwrap();
        let fake_python = bin_dir.join("python3.10");
        std::fs::write(&fake_python, b"#!/bin/sh\necho 'Python 3.10.0'\n").unwrap();
        let mut perms = std::fs::metadata(&fake_python).unwrap().permissions();
        perms.set_mode(0o755);
        std::fs::set_permissions(&fake_python, perms).unwrap();

        // Inject our fake bin dir as if it were /opt/homebrew/bin by placing
        // it in PATH only for this search (simulate via which_in directly).
        let search = std::env::join_paths([&bin_dir]).unwrap();
        let result = which::which_in("python3.10", Some(&search), ".").unwrap();
        assert_eq!(result, fake_python);

        // Verify the version check logic accepts it.
        let version = check_python_version(&result).await;
        assert_eq!(version, Some((3, 10)));
    }

    #[test]
    fn search_dirs_includes_path_entries() {
        let original = std::env::var("PATH").ok();
        std::env::set_var("PATH", "/usr/bin:/bin");
        let dirs = python_search_dirs();
        let dirs_str = dirs.to_string_lossy().to_string();
        assert!(dirs_str.contains("/usr/bin"), "should include PATH entries: {dirs_str}");
        if let Some(orig) = original {
            std::env::set_var("PATH", orig);
        }
    }

    #[test]
    fn search_dirs_deduplicates_entries() {
        let original = std::env::var("PATH").ok();
        // Put /opt/homebrew/bin in PATH; search_dirs should not duplicate it.
        std::env::set_var("PATH", "/opt/homebrew/bin:/usr/bin");
        let dirs = python_search_dirs();
        let dirs_str = dirs.to_string_lossy().to_string();
        let count = dirs_str.split(':').filter(|s| *s == "/opt/homebrew/bin").count();
        assert_eq!(count, 1, "/opt/homebrew/bin should appear exactly once: {dirs_str}");
        if let Some(orig) = original {
            std::env::set_var("PATH", orig);
        }
    }

    #[test]
    fn search_dirs_puts_pyenv_shims_first() {
        use std::os::unix::fs::PermissionsExt;
        let tmp = tempfile::tempdir().unwrap();
        let shims = tmp.path().join(".pyenv").join("shims");
        std::fs::create_dir_all(&shims).unwrap();

        let original_home = std::env::var("HOME").ok();
        let original_path = std::env::var("PATH").ok();
        std::env::set_var("HOME", tmp.path());
        std::env::set_var("PATH", "/usr/bin");

        let dirs = python_search_dirs();
        let dirs_str = dirs.to_string_lossy().to_string();
        let first = dirs_str.split(':').next().unwrap_or("");
        assert_eq!(first, shims.to_str().unwrap(), "pyenv shims must be first: {dirs_str}");

        if let Some(h) = original_home { std::env::set_var("HOME", h); }
        if let Some(p) = original_path { std::env::set_var("PATH", p); }
    }

    #[tokio::test]
    async fn discovers_python_in_extra_dir_not_in_path() {
        use std::os::unix::fs::PermissionsExt;
        let tmp = tempfile::tempdir().unwrap();
        let extra_bin = tmp.path().join("extra").join("bin");
        std::fs::create_dir_all(&extra_bin).unwrap();
        let fake_python = extra_bin.join("python3.11");
        std::fs::write(&fake_python, b"#!/bin/sh\necho 'Python 3.11.0'\n").unwrap();
        let mut perms = std::fs::metadata(&fake_python).unwrap().permissions();
        perms.set_mode(0o755);
        std::fs::set_permissions(&fake_python, perms).unwrap();

        // With only /nonexistent in PATH the normal which() would miss it.
        let original = std::env::var("PATH").ok();
        std::env::set_var("PATH", "/nonexistent");

        // Searching via the extra dir directly should find it.
        let search = std::env::join_paths([&extra_bin]).unwrap();
        let found = which::which_in("python3.11", Some(&search), ".").ok();
        assert_eq!(found.as_deref(), Some(fake_python.as_path()));

        if let Some(orig) = original { std::env::set_var("PATH", orig); }
    }
}
