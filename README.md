# Self-improving Bot

A bot that starts with a small set of tools, but can modify them and create new ones.

Tools are executable programs, but the definition may evolve. Initially they are Flask applications that serve their
OpenAPI schema.

## How to start

The recommended way is to run the root bot in a Docker container:

    docker run -v .:/root/ -w /root -e UV_PROJECT_ENVIRONMENT=/root/.venv-docker ghcr.io/astral-sh/uv:python3.12-alpine uv run bot.py

The bot has two execution modes: interactive, or server. The interactive mode allows a user to send input to the bot
from standard input, and the server mode receives commands through HTTP requests. The interactive mode transparently
starts the server.

The bot starts a small set of tools:

- `chat`: interfaces with an LLM using Ollama
- `start_tool`: the bot registers itself as a tool that can start other tools
- `search_tools`: Flask app that enables the bot to find available tools
- `create_tool`: Flask app that enables the bot to define a new tool
- `inspect_tool`: Flask app that serves the source code of a tool
- `edit_tool`: Flask app that creates new versions of tools
