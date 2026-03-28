/**
 * generate-llms-txt.mjs
 *
 * Auto-generates docs/static/llms.txt from the content directory.
 * Must run AFTER collect-tentacles and sync-root-docs.
 */

import {readFile, writeFile} from 'node:fs/promises';
import {join, dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {BASE_URL, findMdFiles} from './shared.mjs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const CONTENT_DIR = join(__dirname, '..', 'content');
const OUTPUT_PATH = join(__dirname, '..', 'static', 'llms.txt');

const SECTIONS = [
  {dir: 'guides', label: 'Guides'},
  {dir: 'investing', label: 'OctoBot Cloud'},
  {dir: 'creators', label: 'Creators'},
  {dir: 'developers', label: 'Developers'},
];

const HEADER = `# OctoBot

> OctoBot is a free, open-source cryptocurrency trading bot that supports automated trading strategies across 15+ exchanges.

OctoBot is developed by [Drakkar-Software](https://github.com/Drakkar-Software) and is designed to be multi-strategy, multi-exchange, and multi-cryptocurrency. It features a plugin system called "tentacles" that allows extending functionality without modifying core code.

## Documentation

This documentation is organized into three sections:

- [Open Source Guides](${BASE_URL}/guides/octobot): Install, configure, and run OctoBot
- [OctoBot Cloud](${BASE_URL}/investing/introduction): Invest with OctoBot Cloud strategies
- [Creators Guide](${BASE_URL}/creators/getting-started): Build and customize trading strategies
- [Developers Guide](${BASE_URL}/developers/getting-started): Contribute to the OctoBot codebase

## Key Concepts

### Architecture
OctoBot is a Python monorepo organized into packages under \`packages/\`. The build system is Pants. Key packages include Trading (order engine), Evaluators (signal analysis), Commons (shared utilities), and Async Channel (event system).

### Tentacle System
Tentacles are OctoBot's plugin system. They enable adding trading modes, evaluators, and exchange connectors without modifying core code. Tentacles are categorized as:
- **Trading Modes**: Complete trading strategies (Grid, DCA, Daily Trading, AI Trading)
- **Evaluators**: Market analysis tools (Technical Analysis, Social, Real-Time, AI)
- **Exchange Connectors**: Integrations with cryptocurrency exchanges

### Data Flow
1. Exchange data arrives via websocket/REST
2. Async channels distribute data to evaluators
3. Evaluators produce signals (-1 to +1 scale)
4. Strategies combine signals into decisions
5. Trading modes execute orders on exchanges

## Links

- Source Code: https://github.com/Drakkar-Software/OctoBot
- Website: https://www.octobot.cloud
- Discord: https://discord.gg/vHkcb8W
- Telegram: https://t.me/OctoBot_Project`;

function parseFrontmatter(content, filePath) {
  if (!content.startsWith('---')) return null;
  const endIdx = content.indexOf('---', 3);
  if (endIdx === -1) return null;

  const fm = content.substring(3, endIdx);
  // Handle both quoted and unquoted title/description
  const title = fm.match(/^title:\s*"(.+)"/m)?.[1]
    || fm.match(/^title:\s*(.+)/m)?.[1]?.trim();
  const description = fm.match(/^description:\s*"(.+)"/m)?.[1]
    || fm.match(/^description:\s*(.+)/m)?.[1]?.trim();
  let slug = fm.match(/^slug:\s*(.+)/m)?.[1]?.trim();

  if (!title) return null;

  // Derive slug from file path if not in frontmatter
  if (!slug && filePath) {
    const relative = filePath.replace(CONTENT_DIR, '').replace(/\.md$/, '').replace(/\/index$/, '');
    slug = relative.startsWith('/') ? relative : `/${relative}`;
  }

  if (!slug) return null;
  return {title, description: description || '', slug};
}

async function main() {
  console.log('Generating llms.txt...');

  const sectionBlocks = [];

  for (const {dir, label} of SECTIONS) {
    const sectionDir = join(CONTENT_DIR, dir);
    const mdFiles = await findMdFiles(sectionDir);
    const pages = [];

    for (const filePath of mdFiles) {
      const content = await readFile(filePath, 'utf-8');
      const fm = parseFrontmatter(content, filePath);
      if (!fm) continue;
      pages.push(fm);
    }

    // Sort: getting-started first, then alphabetically by slug
    pages.sort((a, b) => {
      if (a.slug.endsWith('/getting-started')) return -1;
      if (b.slug.endsWith('/getting-started')) return 1;
      return a.slug.localeCompare(b.slug);
    });

    const lines = pages.map(p => `- ${BASE_URL}${p.slug}: ${p.description || p.title}`);
    sectionBlocks.push(`### ${label}\n${lines.join('\n')}`);
  }

  const output = `${HEADER}\n\n## Optional\n\n${sectionBlocks.join('\n\n')}\n`;
  await writeFile(OUTPUT_PATH, output, 'utf-8');

  const totalPages = sectionBlocks.reduce((sum, block) => sum + (block.match(/^- /gm) || []).length, 0);
  console.log(`Generated llms.txt with ${totalPages} pages.`);
}

main().catch(err => {
  console.error('Failed to generate llms.txt:', err);
  process.exit(1);
});
