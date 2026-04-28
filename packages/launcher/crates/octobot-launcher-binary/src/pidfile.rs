use std::io;
use std::path::Path;

use sysinfo::{ProcessRefreshKind, RefreshKind, System};

pub(crate) fn write_pid_file(path: &Path, pid: u32) -> io::Result<()> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    std::fs::write(path, pid.to_string())
}

pub(crate) fn read_pid_file(path: &Path) -> io::Result<Option<u32>> {
    if !path.exists() {
        return Ok(None);
    }
    let contents = std::fs::read_to_string(path)?;
    let pid = contents
        .trim()
        .parse::<u32>()
        .map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;
    Ok(Some(pid))
}

pub(crate) fn remove_pid_file(path: &Path) -> io::Result<()> {
    if path.exists() {
        std::fs::remove_file(path)?;
    }
    Ok(())
}

pub(crate) fn is_orphaned_pid(pid: u32, expected_binary_name: &str) -> bool {
    let sys = System::new_with_specifics(
        RefreshKind::new().with_processes(ProcessRefreshKind::new()),
    );
    match sys.process(sysinfo::Pid::from_u32(pid)) {
        None => true,
        Some(proc) => {
            let name = proc.name().to_string_lossy();
            !name.contains(expected_binary_name)
        }
    }
}

#[cfg(test)]
#[allow(clippy::unwrap_used)]
mod tests {
    use super::*;

    #[test]
    fn write_and_read_pid() {
        let tmp = tempfile::tempdir().unwrap();
        let path = tmp.path().join("test.pid");
        write_pid_file(&path, 42).unwrap();
        let result = read_pid_file(&path).unwrap();
        assert_eq!(result, Some(42));
    }

    #[test]
    fn read_missing_returns_none() {
        let tmp = tempfile::tempdir().unwrap();
        let path = tmp.path().join("nonexistent.pid");
        let result = read_pid_file(&path).unwrap();
        assert_eq!(result, None);
    }

    #[test]
    fn orphan_detection() {
        assert!(is_orphaned_pid(99999, "octobot"));
    }
}
