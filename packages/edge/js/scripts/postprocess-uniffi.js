const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');

const replacements = [
  {
    // Use get() instead of getEnforcing() so the module returns null when not
    // registered (e.g. Expo Go, or a build where the native lib was not linked)
    file: path.join(root, 'src', 'NativeOctobotEdgeMobile.ts'),
    from: /TurboModuleRegistry\.getEnforcing</g,
    to: 'TurboModuleRegistry.get<',
  },
  {
    // Guard installRustCrate() against a null installer
    file: path.join(root, 'src', 'index.tsx'),
    from: /if \(!rustInstalled\) \{/,
    to: 'if (!rustInstalled && installer) {',
  },
  {
    // Guard uniffiEnsureInitialized()
    file: path.join(root, 'src', 'index.tsx'),
    from: /if \(!initialized\) \{/,
    to: 'if (!initialized && installer) {',
  },
];

for (const { file, from, to } of replacements) {
  if (!fs.existsSync(file)) continue;
  const source = fs.readFileSync(file, 'utf8');
  const next = source.replace(from, to);
  if (next === source) continue;
  fs.writeFileSync(file, next, 'utf8');
  console.log(`patched ${path.relative(root, file)}`);
}
