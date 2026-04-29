use std::future::Future;
use std::io::{IsTerminal, Write};
use tokio::sync::mpsc::UnboundedReceiver;

const FRAMES: &[&str] = &["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];

pub async fn with_spinner<F, T>(label: &str, fut: F) -> T
where
    F: Future<Output = T>,
{
    if !std::io::stderr().is_terminal() {
        return fut.await;
    }

    let label = label.to_string();
    let (tx, rx) = tokio::sync::oneshot::channel::<()>();

    let handle = tokio::spawn(async move {
        let mut rx = rx;
        let mut i = 0usize;
        loop {
            eprint!("\r{} {}", FRAMES[i % FRAMES.len()], label);
            std::io::stderr().flush().ok();
            i += 1;
            tokio::select! {
                biased;
                _ = &mut rx => break,
                _ = tokio::time::sleep(tokio::time::Duration::from_millis(80)) => {}
            }
        }
        eprint!("\r\x1b[2K");
        std::io::stderr().flush().ok();
    });

    let result = fut.await;
    let _ = tx.send(());
    let _ = handle.await;
    result
}

pub async fn with_streaming_spinner<F, T>(
    initial: &str,
    mut label_rx: UnboundedReceiver<String>,
    fut: F,
) -> T
where
    F: Future<Output = T>,
{
    if !std::io::stderr().is_terminal() {
        return fut.await;
    }

    let initial = initial.to_string();
    let (done_tx, done_rx) = tokio::sync::oneshot::channel::<()>();

    let handle = tokio::spawn(async move {
        let mut done_rx = done_rx;
        let mut i = 0usize;
        let mut label = initial;
        loop {
            eprint!("\r{} {}", FRAMES[i % FRAMES.len()], label);
            std::io::stderr().flush().ok();
            i += 1;
            tokio::select! {
                biased;
                _ = &mut done_rx => break,
                Some(new_label) = label_rx.recv() => {
                    label = new_label;
                }
                _ = tokio::time::sleep(tokio::time::Duration::from_millis(80)) => {}
            }
        }
        eprint!("\r\x1b[2K");
        std::io::stderr().flush().ok();
    });

    let result = fut.await;
    let _ = done_tx.send(());
    let _ = handle.await;
    result
}
