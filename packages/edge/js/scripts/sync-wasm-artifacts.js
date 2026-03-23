const fs = require('node:fs');
const path = require('node:path');

const packageRoot = path.resolve(__dirname, '..');
const wasmPkgRoot = path.join(packageRoot, 'src', 'rust-bridge', 'pkg');
const wasmOutRoot = path.join(packageRoot, 'dist', 'wasm');
const files = [
  'octobot_edge_wasm.js',
  'octobot_edge_wasm_bg.js',
  'octobot_edge_wasm_bg.wasm',
];

fs.mkdirSync(wasmOutRoot, { recursive: true });

for (const file of files) {
  const source = path.join(wasmPkgRoot, file);
  const target = path.join(wasmOutRoot, file);

  if (!fs.existsSync(source)) {
    throw new Error(`Missing wasm artifact: ${source}`);
  }

  fs.copyFileSync(source, target);
}

console.log(`Synced wasm artifacts to ${wasmOutRoot}`);
