/**
 * sync-root-docs.mjs
 *
 * Copies root-level documentation files (CONTRIBUTING.md, CHANGELOG.md)
 * into the docs/content/ directory with Docusaurus frontmatter.
 */

import {readFile, writeFile, mkdir} from 'node:fs/promises';
import {join, dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {DEFAULT_BRANCH, escapeYaml, stripFrontmatter} from './shared.mjs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..', '..');
const OUTPUT_DIR = join(__dirname, '..', 'content', 'developers');

const FILES = [
  {
    src: 'CONTRIBUTING.md',
    dest: 'contributing.md',
    frontmatter: {
      title: 'Contributing',
      description: 'How to contribute to OctoBot. Development guidelines, coding style, and pull request process.',
      keywords: ['contributing', 'development', 'octobot', 'pull request', 'guidelines'],
      slug: '/developers/contributing',
      sidebar_position: 90,
    },
  },
  {
    src: 'CHANGELOG.md',
    dest: 'changelog.md',
    frontmatter: {
      title: 'Changelog',
      description: 'OctoBot release history and changelog. Track new features, improvements, and bug fixes.',
      keywords: ['changelog', 'releases', 'octobot', 'updates', 'version history'],
      slug: '/developers/changelog',
      sidebar_position: 91,
    },
  },
];

function buildFrontmatter(meta) {
  const lines = ['---'];
  lines.push(`title: "${escapeYaml(meta.title)}"`);
  lines.push(`description: "${escapeYaml(meta.description)}"`);
  lines.push(`keywords: [${meta.keywords.map(k => `"${k}"`).join(', ')}]`);
  lines.push(`slug: ${meta.slug}`);
  lines.push(`sidebar_position: ${meta.sidebar_position}`);
  lines.push('format: md');
  lines.push('---');
  return lines.join('\n');
}

/** Adapt relative links to work within the docs site or fall back to GitHub URLs. */
function adaptLinks(content) {
  return content
    // Known root-level docs → docs site paths
    .replace(/\[([^\]]+)\]\(\.\/packages\/README\.md\)/g, '[$1](/developers/packages/overview)')
    .replace(/\[([^\]]+)\]\(\.\/CONTRIBUTING\.md\)/g, '[$1](/developers/contributing)')
    .replace(/\[([^\]]+)\]\(\.\/CHANGELOG\.md\)/g, '[$1](/developers/changelog)')
    // Remaining relative .md links → GitHub source URLs
    .replace(/\[([^\]]+)\]\(\.\/((?!http)[^)]+\.md)\)/g,
      `[$1](https://github.com/Drakkar-Software/OctoBot/blob/${DEFAULT_BRANCH}/$2)`);
}

async function main() {
  console.log('Syncing root documentation files...');

  await mkdir(OUTPUT_DIR, {recursive: true});

  for (const file of FILES) {
    const srcPath = join(ROOT, file.src);
    try {
      let content = stripFrontmatter(await readFile(srcPath, 'utf-8'));
      content = adaptLinks(content);

      const output = `${buildFrontmatter(file.frontmatter)}\n\n${content}\n`;
      const destPath = join(OUTPUT_DIR, file.dest);
      await writeFile(destPath, output, 'utf-8');
      console.log(`  ${file.src} → content/developers/${file.dest}`);
    } catch (err) {
      if (err.code === 'ENOENT') {
        console.warn(`  Warning: ${file.src} not found, skipping.`);
      } else {
        throw err;
      }
    }
  }

  console.log('Done syncing root docs.');
}

main().catch(err => {
  console.error('Failed to sync root docs:', err);
  process.exit(1);
});
