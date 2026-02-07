# OctoBot Node
[![OctoBot-Node-CI](https://github.com/Drakkar-Software/OctoBot-Node/workflows/OctoBot-Node-CI/badge.svg)](https://github.com/Drakkar-Software/OctoBot-Node/actions)
[![Telegram](https://img.shields.io/badge/Telegram-grey.svg?logo=telegram)](https://t.me/OctoBot_Project)
[![Twitter](https://img.shields.io/twitter/follow/DrakkarsOctobot.svg?label=twitter&style=social)](https://x.com/DrakkarsOctoBot)
[![YouTube](https://img.shields.io/youtube/channel/views/UC2YAaBeWY8y_Olqs79b_X8A?label=youtube&style=social)](https://www.youtube.com/@octobot1134)

<p align="middle">
<img src="../tentacles/Services/Interfaces/node_web_interface/public/assets/images/octobot_node_256.png" height="256" alt="OctoBot Node logo">
</p>

<p align="center">
<em>Run any OctoBot, anywhere, with ease</em>
</p>

This project is related to [OctoBot](https://github.com/Drakkar-Software/OctoBot).

## Usage

### CLI

OctoBot-Node provides a command-line interface (CLI) for starting the server and managing the application.

#### Basic Usage

Start the server with default settings:
```bash
python start.py
```

Or if installed via pip:
```bash
octobot_node
```

#### CLI Options

- `-v, --version`: Show OctoBot-Node current version
- `--host HOST`: Host to bind the server to (default: 0.0.0.0 for master in production, 127.0.0.1 otherwise)
- `--port PORT`: Port to bind the server to (default: 8000)
- `--master`: Enable master node mode (schedules tasks)
- `--consumers N`: Number of consumer worker threads (0 disables consumers, default: 0). Can be used with --master
- `--environment {local,production}`: Environment mode (default: from ENVIRONMENT environment variable). Auto-reload is enabled automatically when environment is local
- `--admin-username EMAIL`: Admin username in email format (default: from ADMIN_USERNAME environment variable)
- `--admin-password PASSWORD`: Admin password (default: from ADMIN_PASSWORD environment variable)

#### Examples

Start the server on a custom host and port:
```bash
python start.py --host 127.0.0.1 --port 9000
```

Start as master node (schedules tasks):
```bash
python start.py --master
```

Start with consumer workers:
```bash
python start.py --consumers 4
```

Start as master node with consumer workers:
```bash
python start.py --master --consumers 4
```

Start in development mode (auto-reload enabled automatically):
```bash
python start.py --environment local
```

Start in production mode:
```bash
python start.py --master --environment production
```

Set admin credentials:
```bash
python start.py --master --admin-username admin@example.com --admin-password mypassword
```

Show version:
```bash
python start.py --version
```

### With Redis

For using Redis as the scheduler backend:
```bash
docker run -p 6379:6379 --name redis -d redis redis-server --save 60 1 --loglevel warning
```

## Developers
### Prerequisites

Before proceeding, ensure you have [**Python 3.10+**](https://www.python.org) and [**Node.js 20+**](https://nodejs.org) installed on your system.

Once you have installed Python and Node.js, run the following commands:
```bash
npm install
pip install -r requirements.txt
cp .env.sample .env
```

### Web UI

The Web UI can be used in two modes: **static** and **dynamic (development)**. The Web UI is built using [React](https://github.com/facebook/react), [Vite](https://github.com/vitejs/vite), [TanStack](https://github.com/TanStack) and [shadcn-ui](https://github.com/shadcn-ui/ui).

#### Static Web UI

If you do not need to modify the Web UI code, it is recommended to use the static mode for better performance. 
To build the static assets, run:
```bash
npm run build
```
After building, start the FastAPI server. The static Web UI will be available at [http://localhost:8000/app](http://localhost:8000/app).

#### Dynamic (Development) Web UI

If you plan to actively develop or modify the Web UI, use the dynamic development mode. This provides hot-reload and the latest changes instantly.
To run the Web UI in development mode, use:
```bash
npm --prefix ../tentacles/Services/Interfaces/node_web_interface run ui:dev
```
This will start the development server, typically available at [http://localhost:3000](http://localhost:3000). You can access the UI separately while developing.
For API integration during development, make sure your FastAPI backend server is running simultaneously. The development server will proxy API requests to the backend as configured.

### OpenAPI

Whenever you update or add routes in `tentacles/Services/Interfaces/node_api/api`, you need to regenerate the [OpenAPI specification](https://github.com/OAI/OpenAPI-Specification) and the UI OpenAPI client. This can be done easily with the provided script:
```bash
bash ../tentacles/Services/Interfaces/node_web_interface/generate-client.sh
```

### API Server

The API server is built using [FastAPI](https://github.com/fastapi) and provides the backend REST endpoints and websocket interface for OctoBot Node.

#### Running the FastAPI Server

You can start the API server using the CLI (recommended):

```bash
python start.py --master
```

Or directly with uvicorn:

```bash
uvicorn tentacles.Services.Interfaces.node_api_interface.node_api_interface:NodeApiInterface.create_app --factory --host 0.0.0.0 --port 8000
```

- By default, the server runs on [http://localhost:8000](http://localhost:8000).
- You can configure environment variables via `.env`, including host, port, and scheduler/backend settings.
- For development: Use `--environment local` flag. Auto-reload is enabled automatically in local environment.
- For production: Use `--master --environment production` to enable master mode in production.
- The FastAPI server always runs with a single worker (default FastAPI behavior).
- Consumer workers are configured separately using `--consumers N`.

##### Environment Variables

Some key `.env` variables:
- `SCHEDULER_REDIS_URL` (if using Redis as backend)
- `SCHEDULER_SQLITE_FILE` (if using SQLite, default: "tasks.db")
- `SCHEDULER_WORKERS` (number of consumer workers, default: 0, can be overridden with --consumers)
- `ENVIRONMENT` (environment mode: "local" or "production", default: "production")
- `ADMIN_USERNAME` (admin username in email format, can be overridden with --admin-username)
- `ADMIN_PASSWORD` (admin password, can be overridden with --admin-password)

Note: Master mode is controlled via the `--master` CLI flag, not via environment variables.

See `.env.sample` for all options, and adjust as needed.

#### Scheduler

The task scheduler is automatically started together with the FastAPI server through import of the `octobot_node/scheduler` module. The scheduler uses [Huey](https://github.com/coleifer/huey) for task queue management.

- **No manual launch needed** — scheduler and consumers are managed automatically on startup.
- Configuration for the scheduler backend (Redis or SQLite) is picked up from environment variables.
- Consumer workers are started automatically if `SCHEDULER_WORKERS > 0` (or `--consumers N` is used).
- Master mode is enabled via the `--master` CLI flag and allows the node to schedule tasks.
- A node can be both a master (schedules tasks) and run consumer workers simultaneously.
