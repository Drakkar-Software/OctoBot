---
title: "Running Tests"
description: "Learn how automated tests are working on the OctoBot open source Python repositories using pytest git github actions."
sidebar_position: 4
---



# Tests

Each OctoBot repository test suite is run using <a href="https://docs.pytest.org/" rel="nofollow">pytest</a> on <a href="https://docs.github.com/actions" rel="nofollow">GitHub Action</a> and can be run locally on a development environment.

## Requirements

To run OctoBot's tests, an OctoBot development environment is necessary,
development environment setup is described on the [Setup your environment section](setup-your-environment)

## OctoBot engine

To run OctoBot's engine tests, use the _pytest tests_ in OctoBot's root folder :

```bash
pytest tests
```

This will run all tests in the test folder.

## Tentacles

To run OctoBot's tentacles tests, use the `pytest tentacles` command in OctoBot's root folder :

```bash
pytest tentacles
```

This will run all tests in the **tentacles** folder. Testing tentacles works only if tentacles
are installed on the tested OctoBot. See the
[developer environment](setup-your-environment)
to install tentacles.
