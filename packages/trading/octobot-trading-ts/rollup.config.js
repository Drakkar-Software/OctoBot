import { readFileSync } from 'fs';

const pkg = JSON.parse(readFileSync('./package.json', 'utf-8'));

export default {
  input: './dist/index.js',
  output: {
    dir: './dist/cjs',
    format: 'cjs',
    preserveModules: true,
    preserveModulesRoot: 'dist',
    exports: 'named',
    entryFileNames: '[name].js',
  },
  external: [
    ...Object.keys(pkg.dependencies || {}),
    ...Object.keys(pkg.peerDependencies || {}),
    'fs',
    'path',
    'crypto',
    'http',
    'https',
    'url',
    'events',
  ],
};
