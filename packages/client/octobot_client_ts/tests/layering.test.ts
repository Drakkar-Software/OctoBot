import { describe, it, expect } from 'vitest'
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, relative } from 'node:path'

// Architecture, enforced: tier 1 (identity/ transport/ crypto/ collections/
// node-api/ protocol/ internal/) never imports tier 2 (client/), and
// protocol/ stays I/O-free — it never imports transport/, identity/, or
// crypto/. Nothing in this package should ever need to update this test to
// "make it pass" — a failure here means a file landed in the wrong tier.

const SRC = join(import.meta.dirname, '..', 'src')
const TIER_1_DIRS = ['identity', 'transport', 'crypto', 'collections', 'node-api', 'protocol', 'internal']

function listTsFiles(dir: string): string[] {
  const out: string[] = []
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry)
    if (statSync(full).isDirectory()) out.push(...listTsFiles(full))
    else if (entry.endsWith('.ts')) out.push(full)
  }
  return out
}

function importSpecifiers(file: string): string[] {
  const text = readFileSync(file, 'utf8')
  const specifiers: string[] = []
  const re = /from\s+['"]([^'"]+)['"]/g
  let m: RegExpExecArray | null
  while ((m = re.exec(text))) specifiers.push(m[1])
  return specifiers
}

describe('layering: tier 1 never imports client/', () => {
  for (const dir of TIER_1_DIRS) {
    const dirPath = join(SRC, dir)
    let files: string[]
    try {
      files = listTsFiles(dirPath)
    } catch {
      continue
    }
    for (const file of files) {
      it(`${relative(SRC, file)} does not import client/`, () => {
        const bad = importSpecifiers(file).filter((s) => s.includes('/client/') || s === '../client' || s.startsWith('../client/'))
        expect(bad).toEqual([])
      })
    }
  }
})

describe('layering: protocol/ stays I/O-free', () => {
  const files = listTsFiles(join(SRC, 'protocol'))
  for (const file of files) {
    it(`${relative(SRC, file)} does not import transport/, identity/, or crypto/`, () => {
      const bad = importSpecifiers(file).filter(
        (s) => s.startsWith('../transport/') || s.startsWith('../identity/') || s.startsWith('../crypto/')
          || s.startsWith('../../transport/') || s.startsWith('../../identity/') || s.startsWith('../../crypto/'),
      )
      expect(bad).toEqual([])
    })
  }
})
