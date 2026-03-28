---
title: Getting Started
description: Set up your OctoBot development environment. Clone the repo, install dependencies, run tests, and understand the codebase architecture.
keywords: [octobot, development, contributing, setup, environment, architecture]
sidebar_position: 1
---

# Developer Guide

This section is for developers who want to contribute to the OctoBot codebase. It covers the development environment, architecture, packages, and contribution workflow.

## Development Setup

### Prerequisites

- Python 3.13+
- Git
- [Pants](https://www.pantsbuild.org/) build system (auto-installed)
- Node.js 22+ (for web interface and docs)
- Rust toolchain (optional, for Rust-accelerated packages)

### Clone and Install

```bash
git clone https://github.com/Drakkar-Software/OctoBot.git
cd OctoBot
pip install -r dev_requirements.txt
pip install -e .
```

### Running Tests

```bash
# Run all tests for a package
cd packages/commons
pytest tests

# Run tests with Pants
pants test packages/commons::
```

### Linting

```bash
pylint --rcfile=standard.rc octobot/
```

## Repository Structure

```
OctoBot/
  octobot/           # Main application
  packages/           # Self-contained packages (14+)
  infra/              # Infrastructure (Ansible, deploy)
  tests/              # Integration tests
  docs/               # This documentation
  pants.toml          # Pants build config
  BUILD               # Root build file
```

## Next Steps

- [Architecture](/developers/architecture/overview) - Understand the system design
- [Packages](/developers/packages/overview) - Explore each package
- [Infrastructure](/developers/infrastructure/) - Deployment and operations
- [Contributing](/developers/contributing) - Coding guidelines and PR process
