fn main() {
    println!("cargo:rerun-if-env-changed=OCTOBOT_LAUNCHER_UPDATE_PUBKEY");
    let hex = std::env::var("OCTOBOT_LAUNCHER_UPDATE_PUBKEY")
        .unwrap_or_else(|_| "0".repeat(64));
    println!("cargo:rustc-env=LAUNCHER_UPDATE_PUBKEY_HEX={hex}");
    let target = std::env::var("TARGET").unwrap_or_default();
    println!("cargo:rustc-env=LAUNCHER_TARGET_TRIPLE={target}");
}
