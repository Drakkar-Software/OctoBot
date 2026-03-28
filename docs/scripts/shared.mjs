/**
 * Shared constants and utilities used by all docs collection scripts.
 */

import {readdir} from 'node:fs/promises';
import {join} from 'node:path';

export const BASE_URL = 'https://docs.octobot.cloud';
export const DEFAULT_BRANCH = 'dev';

/**
 * Extract the first contiguous paragraph from markdown content,
 * truncated to max 160 characters for SEO meta descriptions.
 */
export function extractDescription(content, fallback) {
  const paragraphLines = [];
  let started = false;
  for (const line of content.split('\n')) {
    const trimmed = line.trim();
    if (!started) {
      if (trimmed && !trimmed.startsWith('#') && !trimmed.startsWith('---')) {
        started = true;
        paragraphLines.push(trimmed);
      }
    } else {
      if (!trimmed || trimmed.startsWith('#')) break;
      paragraphLines.push(trimmed);
    }
  }
  const firstParagraph = paragraphLines.join(' ').replace(/\s+/g, ' ').trim();

  if (firstParagraph.length > 10 && firstParagraph.length <= 160) {
    return firstParagraph;
  }
  if (firstParagraph.length > 160) {
    const truncated = firstParagraph.substring(0, 157);
    const lastSpace = truncated.lastIndexOf(' ');
    return (lastSpace > 100 ? truncated.substring(0, lastSpace) : truncated) + '...';
  }
  return fallback;
}

/** Escape special characters for safe inclusion in YAML frontmatter values. */
export function escapeYaml(value) {
  return value
    .replace(/\\/g, '\\\\')
    .replace(/"/g, '\\"')
    .replace(/\n/g, ' ')
    .replace(/\r/g, '');
}

/** Convert a PascalCase/camelCase name to a URL-friendly slug. */
export function toSlug(name) {
  return name
    .replace(/([a-z])([A-Z])/g, '$1-$2')
    .replace(/[_\s]+/g, '-')
    .toLowerCase();
}

/** Strip leading YAML frontmatter (--- ... ---) from markdown content. */
export function stripFrontmatter(content) {
  if (!content.startsWith('---')) return content;
  const endIdx = content.indexOf('---', 3);
  if (endIdx === -1) return content;
  return content.substring(endIdx + 3).trim();
}

/**
 * Recursively find all .md files under a directory.
 * Optional filter function receives relative path from baseDir.
 */
export async function findMdFiles(dir, filter) {
  const results = [];

  async function walk(current) {
    let entries;
    try {
      entries = await readdir(current, {withFileTypes: true});
    } catch {
      return;
    }
    for (const entry of entries) {
      const fullPath = join(current, entry.name);
      if (entry.isDirectory()) {
        await walk(fullPath);
      } else if (entry.isFile() && entry.name.endsWith('.md')) {
        if (!filter || filter(fullPath)) {
          results.push(fullPath);
        }
      }
    }
  }

  await walk(dir);
  return results;
}
