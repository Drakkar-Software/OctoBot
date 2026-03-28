# OctoBot Documentation

Built with [Docusaurus 3](https://docusaurus.io/). Supports English and French (i18n).

## Setup

```bash
cd docs
npm install
```

Requires Node.js >= 20.

## Development

```bash
npm start
```

Runs the pre-collect step (generates tentacle docs, syncs root docs, generates `llms.txt`), then starts the dev server at `http://localhost:3000`.

## Build

```bash
npm run build
```

Output goes to `docs/build/`. The pre-collect step runs automatically before the build.

### Collect step (manual)

The collect step generates content from tentacles and syncs a few root-level files. It runs automatically on `start` and `build`, but you can run it manually:

```bash
npm run collect
```

Generated files are gitignored — never commit them:

- `content/guides/exchanges.md` and `content/guides/exchanges/`
- `content/guides/strategies/`
- `content/creators/`
- `content/developers/contributing.md` and `content/developers/changelog.md`
- `static/llms.txt`

## Images and Git LFS

Images in `docs/static/` are stored in [Git LFS](https://git-lfs.com/) — the repo only contains LFS pointers, not the actual image blobs.

### First-time setup

Install Git LFS once per machine:

```bash
brew install git-lfs   # macOS
git lfs install
```

After cloning or pulling, fetch the actual image files:

```bash
git lfs pull
```

### Adding new images

Drop images into `docs/static/images/`. Git will automatically track them via LFS (configured in `.gitattributes` at the repo root). No extra steps needed — just `git add` and commit as usual.

Supported formats: `.png`, `.jpg`, `.jpeg`, `.webp`.

### Checking LFS status

```bash
git lfs ls-files          # list all LFS-tracked files
git lfs status            # show pending LFS changes
```
