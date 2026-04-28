use std::collections::HashMap;
use std::time::{Duration, Instant};

use parking_lot::Mutex;

const MAX_FAILURES: u32 = 10;
const WINDOW_SECS: u64 = 60;
const LOCKOUT_SECS: u64 = 300;
const MAX_ENTRIES: usize = 1024;

#[derive(Debug)]
struct LockoutEntry {
    fail_count: u32,
    window_start: Instant,
    locked_until: Option<Instant>,
}

#[derive(Debug)]
pub struct Lockout {
    inner: Mutex<HashMap<String, LockoutEntry>>,
}

impl Lockout {
    pub fn new() -> Self {
        Self {
            inner: Mutex::new(HashMap::new()),
        }
    }

    pub fn check(&self, ip: &str) -> bool {
        let map = self.inner.lock();
        match map.get(ip) {
            Some(entry) => {
                if let Some(until) = entry.locked_until {
                    Instant::now() >= until
                } else {
                    true
                }
            }
            None => true,
        }
    }

    pub fn record_failure(&self, ip: &str) {
        let mut map = self.inner.lock();
        let now = Instant::now();

        if map.len() >= MAX_ENTRIES && !map.contains_key(ip) {
            let oldest_key = map
                .iter()
                .min_by_key(|(_, v)| v.window_start)
                .map(|(k, _)| k.clone());
            if let Some(key) = oldest_key {
                map.remove(&key);
            }
        }

        let entry = map.entry(ip.to_string()).or_insert_with(|| LockoutEntry {
            fail_count: 0,
            window_start: now,
            locked_until: None,
        });

        if now.duration_since(entry.window_start) > Duration::from_secs(WINDOW_SECS) {
            entry.fail_count = 0;
            entry.window_start = now;
            entry.locked_until = None;
        }

        entry.fail_count += 1;

        if entry.fail_count >= MAX_FAILURES {
            entry.locked_until = Some(now + Duration::from_secs(LOCKOUT_SECS));
        }
    }

    pub fn record_success(&self, ip: &str) {
        let mut map = self.inner.lock();
        map.remove(ip);
    }

    pub fn unlock(&self, ip: &str) {
        let mut map = self.inner.lock();
        if let Some(entry) = map.get_mut(ip) {
            entry.locked_until = None;
            entry.fail_count = 0;
        }
    }

    pub fn len(&self) -> usize {
        self.inner.lock().len()
    }

    pub fn is_empty(&self) -> bool {
        self.inner.lock().is_empty()
    }
}

impl Default for Lockout {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    #![allow(clippy::unwrap_used, clippy::expect_used)]
    use super::*;

    #[test]
    fn ten_failed_attempts_locks_ip() {
        let lockout = Lockout::new();
        let ip = "192.168.1.1";

        assert!(lockout.check(ip));

        for _ in 0..10 {
            lockout.record_failure(ip);
        }

        assert!(!lockout.check(ip));
    }

    #[test]
    fn lru_capped() {
        let lockout = Lockout::new();

        for i in 0..2000_u32 {
            let ip = format!("10.0.{}.{}", i / 256, i % 256);
            lockout.record_failure(&ip);
        }

        assert!(lockout.len() <= MAX_ENTRIES);
    }

    #[test]
    fn separate_ips_dont_interfere() {
        let lockout = Lockout::new();
        let ip_a = "10.0.0.1";

        for _ in 0..10 {
            lockout.record_failure(ip_a);
        }

        assert!(!lockout.check(ip_a));
        assert!(lockout.check("10.0.0.2"));
    }

    #[test]
    fn expires_after_lockout_manual_unlock() {
        let lockout = Lockout::new();
        let ip = "10.1.2.3";

        for _ in 0..10 {
            lockout.record_failure(ip);
        }

        assert!(!lockout.check(ip));
        lockout.unlock(ip);
        assert!(lockout.check(ip));
    }
}
