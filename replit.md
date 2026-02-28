# Obmen - Telegram Gift Mini App

## Overview
A Telegram Mini App (Web App) for managing and displaying gifts. Built with FastAPI (Python) backend serving a Jinja2/HTML frontend, with a Telegram bot (aiogram) for user registration and admin commands.

## Architecture
- **Backend/Frontend**: FastAPI serving HTML via Jinja2 templates on port 5000
- **Database**: SQLite via aiosqlite (`database.db`)
- **Bot**: aiogram v3 Telegram bot (`bot.py`) — run separately
- **Static files**: Gift images served from `gifts/` directory

## Key Files
- `main.py` — FastAPI app entrypoint (port 5000)
- `bot.py` — Telegram bot (run with `python bot.py`)
- `config.py` — Bot token, admin ID, gift configuration
- `database.py` — SQLite async database helpers
- `templates/index.html` — Main Mini App UI

## Configuration (config.py)
- `BOT_TOKEN` — Telegram bot token
- `WEBAPP_URL` — URL of the deployed FastAPI app (used by bot for Mini App button)
- `ADMIN_ID` — Telegram user ID for admin commands
- `GIFTS` — Gift definitions (id, name, photo path, required_amount)

## API Endpoints
- `GET /` — Serves the Mini App HTML
- `POST /api/init` — Initialize user session, returns gift config and user's gifts
- `GET /api/leaderboard` — Returns top 50 users by total gifts

## Running
- **Web app**: `python main.py` (workflow: "Start application", port 5000)
- **Bot**: `python bot.py` (run separately)

## Deployment
- Target: VM (always-running, needed for bot + web server)
- Run: `gunicorn --bind=0.0.0.0:5000 --reuse-port --worker-class=uvicorn.workers.UvicornWorker main:app`
