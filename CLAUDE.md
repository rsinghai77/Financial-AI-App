# CLAUDE.md — FinApp Development Instructions

## Always Read First
Before generating any code, read these spec files in order:
1. `openspec/guardrails.yaml` — **NON-NEGOTIABLE constraints. Never violate these.**
2. `openspec/project.yaml` — Project metadata, tech stack, coding standards
3. `openspec/architecture.yaml` — Layer structure and dependency rules
4. `openspec/data_models.yaml` — Data schemas (read before touching any model)
5. `openspec/requirements.yaml` — What features to build
6. `openspec/agents.yaml` — When building AI agent code
7. `openspec/mcp.yaml` — When building MCP servers
8. `openspec/gui.yaml` — When building Streamlit pages

## Project Structure
```
src/finapp/
├── config.py                    # pydantic-settings — all configuration here
├── domain/                      # Pure business logic — NO external dependencies
│   ├── models/                  # Pydantic models (Portfolio, Holding, Transaction, etc.)
│   ├── calculators/             # Pure financial calculation functions
│   └── repositories/            # Abstract repository interfaces (ABCs)
├── infrastructure/              # SQLAlchemy, cache, external API wrappers
│   ├── database.py              # SQLAlchemy engine + session factory
│   ├── orm_models.py            # SQLAlchemy ORM table definitions
│   ├── repositories/            # Concrete repository implementations
│   └── cache/                   # Disk-based caching
├── mcp_servers/                 # MCP server implementations (6 servers)
├── app/                         # Application layer: services + agents
│   ├── services/                # Business use-cases
│   └── agents/                  # Claude AI agent implementations
└── gui/                         # Streamlit pages and components
    ├── main.py                  # App entry point
    ├── pages/                   # One file per page
    └── components/              # Shared UI components
```

## Hard Rules (from guardrails.yaml)
- **NEVER hardcode API keys** — use `config.py` (pydantic-settings reads from `.env`)
- **NEVER import streamlit** in domain/, app/agents/, or app/services/
- **NEVER write raw SQL** — use SQLAlchemy ORM
- **EVERY AI response** with financial content must end with the disclaimer from guardrails.yaml
- **ALWAYS** use `async/await` for I/O operations
- **ALWAYS** include type annotations on public functions
- **ALL** financial calculations must use `Decimal` or `numpy` — never bare floats for currency

## Running the App
```bash
# Install dependencies
uv sync

# Set up environment
cp .env.example .env
# Edit .env with your API keys

# Run database migrations
uv run alembic upgrade head

# Start the application
uv run streamlit run src/finapp/gui/main.py
```

## Running Tests
```bash
uv run pytest
```

## Code Style
- Formatter: `uv run ruff format src/`
- Linter: `uv run ruff check src/`
- Type checker: `uv run mypy src/`
