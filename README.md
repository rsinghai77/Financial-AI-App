# FinApp — AI-Enabled Financial Application

> A personal portfolio management and financial intelligence platform powered by Claude AI agents, MCP servers, and a Streamlit interface. Built using **Spec Driven Development (SDD)** with OpenSpec.

---

## Table of Contents

- [What This App Does](#what-this-app-does)
- [Architecture](#architecture)
- [Core Functionality](#core-functionality)
- [AI Agents](#ai-agents)
- [MCP Servers](#mcp-servers)
- [Technology Stack](#technology-stack)
- [How to Run](#how-to-run)
- [Deployment](#deployment)
- [Project Structure](#project-structure)
- [Future Enhancements](#future-enhancements)

---

## What This App Does

FinApp is an AI-enabled personal financial application that helps individual investors manage their portfolios, analyse risk, research markets, and plan for long-term financial goals — all through a conversational AI interface backed by real market data.

### Key Capabilities

- **Portfolio Tracking** — Add, manage, and value holdings across multiple accounts (brokerage, IRA, 401k, crypto). Tracks cost basis, tax lots, and unrealised gain/loss per position.
- **AI Financial Advisors** — Seven Claude-powered agents provide streaming analysis on portfolio composition, risk, market research, news, financial planning, and trade review.
- **Market Data** — Real-time quotes, historical OHLCV charts, technical indicators (RSI, MACD, Bollinger Bands, SMA/EMA), and fundamental data (P/E, EPS, margins) via Yahoo Finance.
- **Risk Analytics** — Value at Risk (VaR) at 95%/99% confidence, Sharpe and Sortino ratios, maximum drawdown, beta, correlation heatmaps, and historical stress tests (2008, 2020, 2022, dot-com).
- **Financial News** — Aggregated news with automatic keyword-based sentiment scoring, SEC EDGAR filing retrieval, and portfolio-relevant filtering.
- **Financial Planning** — Goal tracking, compound growth projections in three scenarios (conservative/base/optimistic), IRR calculations, and retirement readiness analysis.
- **Trade Review** — Pre-trade checklist covering market context, portfolio impact, risk change, capital gains tax estimates, and wash-sale rule checks.
- **Reports & Export** — Portfolio CSV export and PDF performance reports.

### Design Philosophy

FinApp was built using **Spec Driven Development (SDD)** — all requirements, architecture, data models, agent contracts, and guardrails were specified in [OpenSpec YAML files](openspec/) *before* any code was written. This produces a highly coherent codebase where every implementation decision traces back to an explicit specification.

---

## Architecture

FinApp follows a **strict five-layer architecture** with enforced dependency rules between layers.

```
┌──────────────────────────────────────────────────────────┐
│  PRESENTATION LAYER  (Streamlit)                          │
│  src/finapp/gui/pages/   — 7 pages + shared components   │
│  No business logic. No direct database access.           │
├──────────────────────────────────────────────────────────┤
│  APPLICATION LAYER                                        │
│  src/finapp/app/agents/  — 7 Claude AI agents            │
│  src/finapp/app/services/ — 4 use-case services          │
│  No Streamlit imports. Orchestrates domain + MCP.        │
├──────────────────────────────────────────────────────────┤
│  DOMAIN LAYER                                             │
│  src/finapp/domain/models/      — 7 Pydantic models      │
│  src/finapp/domain/calculators/ — pure financial math    │
│  src/finapp/domain/repositories/ — abstract interfaces  │
│  Pure Python only. No I/O. No external dependencies.     │
├──────────────────────────────────────────────────────────┤
│  INFRASTRUCTURE LAYER                                     │
│  src/finapp/infrastructure/  — SQLAlchemy ORM + cache    │
│  Implements domain repository interfaces.                │
├──────────────────────────────────────────────────────────┤
│  MCP SERVER LAYER                                         │
│  src/finapp/mcp_servers/  — 6 tool servers               │
│  Exposes tools to AI agents via MCP protocol.            │
└──────────────────────────────────────────────────────────┘
```

### Data Flow

```
User Input (GUI)
    → App Service or Agent
        → MCP Server (tool call)
            → External API (yfinance / NewsAPI / Brave)
            → Infrastructure (SQLite via Repository)
        → Domain Calculator (pure function)
    → Streaming response back to GUI
```

### Key Architectural Patterns

| Pattern | Where Used | Why |
|---------|-----------|-----|
| Layered Architecture | Entire app | Clear separation of concerns |
| Repository Pattern | Infrastructure | Decouples DB from business logic; enables SQLite→PostgreSQL swap |
| Cache-Aside | Market data MCP | Reduces API calls; respects free-tier rate limits |
| Tool-Use Loop | AI Agents | Agents call MCP tools autonomously; results fed back to Claude |
| Streaming | AI Advisor page | Tokens stream to UI as generated — no waiting for full response |
| Event-Driven (future) | Background refresh | Planned for v0.2 price alerts |

---

## Core Functionality

### Portfolio Management

- Add holdings with ticker, quantity, cost basis, purchase date, asset class, and notes
- Supports fractional shares (Decimal precision to 6 decimal places)
- Multiple accounts per portfolio (brokerage, IRA, Roth IRA, 401k, crypto, savings)
- Tax lot tracking per holding for accurate capital gains calculation
- Transactions are **immutable** (append-only) — corrections recorded as new transactions
- Asset allocation breakdown by class (equity, ETF, bond, crypto, REIT, etc.)

### Market Data

- **Quotes**: Price, change, change %, volume, 52-week high/low, market cap
- **Historical OHLCV**: Up to 5+ years of daily/weekly/monthly bars
- **Technical Indicators**: RSI, MACD, SMA (20/50/200), EMA (12/26), Bollinger Bands, ATR
- **Fundamental Data**: P/E, P/B, P/S, EV/EBITDA, dividend yield, EPS, revenue, margins, ROE, debt/equity
- **Caching**: 5-min quotes, 1-hr historical, 24-hr fundamentals — persists across sessions
- **Staleness warnings**: UI shows age of cached data (GRD-OPS-003 compliance)

### Risk Analysis

| Metric | Method | Description |
|--------|--------|-------------|
| VaR 95%/99% (1-day) | Historical simulation | Dollar + percentage maximum expected loss |
| Sharpe Ratio | Annualised return / volatility | Risk-adjusted return quality |
| Sortino Ratio | Return / downside deviation | Downside-only risk adjustment |
| Max Drawdown | Peak-to-trough on return series | Worst historical loss from a peak |
| Portfolio Beta | Covariance / benchmark variance | Market sensitivity |
| Correlation Matrix | Pairwise Pearson correlation | Visualised as heatmap |
| Stress Tests | Asset-class drawdown scenarios | Dollar loss under historical crashes |

**Stress test scenarios**: 2008 Financial Crisis (S&P −57%), 2020 COVID Crash (S&P −34%), 2022 Rate Hike Cycle (S&P −25%), Dot-Com Bubble (S&P −49%), Custom (slider from −5% to −70%).

### Financial Planning

- Goal definition: retirement, house down payment, education, emergency fund, travel, custom
- Three-scenario compound growth projections (conservative / base / optimistic)
- Always includes inflation adjustment (default 3%) and the note: *"Past performance does not guarantee future results"*
- IRR calculation for arbitrary cash-flow series
- Jensen's Alpha for portfolio manager evaluation

### Financial Compliance (Guardrails)

FinApp enforces SEC-style compliance guardrails defined in [`openspec/guardrails.yaml`](openspec/guardrails.yaml):

- Every AI response with financial analysis includes a mandatory disclaimer
- AI agents never say "buy", "sell now", "guaranteed", or "you will make money"
- Tax calculations always include the tax professional disclaimer
- Projections always show three scenarios and state assumptions
- No API keys hardcoded — all secrets via `.env`
- No SQL injection — SQLAlchemy ORM only
- User portfolio data never sent to external APIs (only ticker symbols)

---

## AI Agents

All agents use **claude-sonnet-4-6** with streaming, tool use, and temperature 0.3 (for consistent financial reasoning).

| Agent | Role | Key Tools |
|-------|------|-----------|
| **FinApp Assistant** (Orchestrator) | Classifies intent and routes to specialist agents | portfolio-mcp |
| **Portfolio Advisor** | Allocation analysis, rebalancing, concentration risk, performance drivers | portfolio-mcp, market-data-mcp, calculator-mcp |
| **Risk Analyst** | VaR, drawdown, stress tests, correlation, risk threshold monitoring | calculator-mcp, market-data-mcp |
| **Market Researcher** | Bull/bear security analysis, technicals, fundamentals, peer comparison | market-data-mcp, news-mcp, search-mcp |
| **News Sentinel** | Portfolio-relevant news digest, sentiment, SEC filings, MNPI detection | news-mcp, portfolio-mcp |
| **Financial Planner** | Goal setting, savings projections, retirement readiness, IRR | calculator-mcp, portfolio-mcp |
| **Trade Reviewer** | Pre-trade checklist, tax impact, wash-sale check, concentration change | calculator-mcp, market-data-mcp, portfolio-mcp |

### How Agent Tool Use Works

```
User message
    → Agent sends message + tool definitions to Claude API
    → Claude returns tool_use block (e.g., get_quote)
    → Agent dispatches to MCP server function
    → Tool result fed back to Claude
    → Claude continues (possibly calling more tools)
    → Final text response streamed to Streamlit UI
```

---

## MCP Servers

Six MCP servers expose domain capabilities as callable tools. Each runs in-process using `FastMCP` with stdio transport.

| Server | Tools | External APIs |
|--------|-------|---------------|
| **market-data-mcp** | `get_quote`, `get_historical_prices`, `get_fundamentals`, `get_technical_indicators` | yfinance (free), Alpha Vantage (optional) |
| **news-mcp** | `search_news`, `get_sentiment_score`, `get_sec_filings`, `summarize_article` | NewsAPI (optional), SEC EDGAR (free) |
| **portfolio-mcp** | `get_portfolio`, `add_holding`, `update_holding`, `get_performance`, `get_transactions` | SQLite (local) |
| **calculator-mcp** | `calculate_var`, `calculate_sharpe`, `run_stress_test`, `calculate_irr`, `optimize_weights`, `project_future_value`, `calculate_tax_impact` | None (internal numpy/scipy) |
| **search-mcp** | `web_search` | Brave Search API (optional) |
| **export-mcp** | `export_portfolio_csv`, `generate_performance_report` | None (local file generation) |

---

## Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Language | Python | ≥ 3.12 |
| Package Manager | uv | latest |
| GUI Framework | Streamlit | ≥ 1.42 |
| AI Provider | Anthropic Claude | claude-sonnet-4-6 |
| AI SDK | anthropic Python SDK | ≥ 0.49 |
| MCP Protocol | mcp Python SDK | ≥ 1.5 |
| ORM | SQLAlchemy (async) | ≥ 2.0 |
| Database (dev) | SQLite + aiosqlite | — |
| Database (prod) | PostgreSQL | — |
| Market Data | yfinance | ≥ 0.2.55 |
| HTTP Client | httpx (async) | ≥ 0.27 |
| Data Processing | pandas, numpy | ≥ 2.2, ≥ 1.26 |
| Financial Math | scipy | ≥ 1.12 |
| Visualisation | Plotly | ≥ 5.24 |
| Caching | diskcache | ≥ 5.6 |
| Configuration | pydantic-settings | ≥ 2.7 |
| PDF Export | reportlab | ≥ 4.2 |
| Linting | ruff | ≥ 0.8 |
| Type Checking | mypy | ≥ 1.11 |
| Testing | pytest + hypothesis | ≥ 8.0 |

---

## How to Run

### Prerequisites

- Python 3.12 or higher
- [uv](https://docs.astral.sh/uv/getting-started/installation/) installed

### Quick Start

```bash
# 1. Clone the repository
git clone <repository-url>
cd Financial-AI-App

# 2. Install all dependencies
uv sync

# 3. Configure environment
cp .env.example .env
```

Edit `.env` and add your API keys:

```env
# Required — all AI features depend on this
ANTHROPIC_API_KEY=sk-ant-...

# Optional — app works without these (see fallbacks below)
ALPHA_VANTAGE_API_KEY=your_key    # Enhanced market data (free tier: 5 req/min)
NEWS_API_KEY=your_key             # Financial news (free tier: 100 req/day)
BRAVE_SEARCH_API_KEY=your_key     # Web search for Market Researcher agent
```

```bash
# 4. Run the application
uv run streamlit run src/finapp/gui/main.py
```

Open `http://localhost:8501` in your browser.

### API Keys

| Key | Required | Where to Get | Free Tier |
|-----|----------|-------------|-----------|
| `ANTHROPIC_API_KEY` | **Yes** | [console.anthropic.com](https://console.anthropic.com) | Pay-as-you-go |
| `ALPHA_VANTAGE_API_KEY` | No | [alphavantage.co](https://www.alphavantage.co/support/#api-key) | 5 req/min |
| `NEWS_API_KEY` | No | [newsapi.org](https://newsapi.org/register) | 100 req/day |
| `BRAVE_SEARCH_API_KEY` | No | [brave.com/search/api](https://brave.com/search/api/) | 2,000 req/month |

**Without optional keys**: Market data uses yfinance (free, no key required). News shows a configuration message. Web search is disabled.

### Running Tests

```bash
# All tests with coverage
uv run pytest

# Verbose output
uv run pytest -v

# Specific module
uv run pytest tests/domain/test_risk_calculator.py -v

# Coverage HTML report
uv run pytest --cov=src/finapp --cov-report=html
open htmlcov/index.html
```

### Code Quality

```bash
# Lint
uv run ruff check src/

# Format
uv run ruff format src/

# Type check
uv run mypy src/finapp/domain/ src/finapp/app/
```

---

## Deployment

### Development (Current)

Single-process mode — Streamlit, AI agents, and all MCP servers run in one Python process with SQLite.

```bash
uv run streamlit run src/finapp/gui/main.py
```

### Production — Docker (Recommended)

Create a `Dockerfile` at the project root:

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY . .

RUN pip install uv && uv sync --no-dev

EXPOSE 8501

CMD ["uv", "run", "streamlit", "run", "src/finapp/gui/main.py", \
     "--server.port=8501", "--server.address=0.0.0.0", \
     "--server.headless=true"]
```

```bash
docker build -t finapp .
docker run -p 8501:8501 --env-file .env finapp
```

### Production — PostgreSQL

Switch the database URL in `.env`:

```env
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/finapp
```

Add `asyncpg` to dependencies:

```bash
uv add asyncpg
```

Run Alembic migrations (once Alembic is configured):

```bash
uv run alembic upgrade head
```

No other code changes required — the repository pattern abstracts the database engine.

### Production — Cloud (Streamlit Community Cloud)

1. Push the repository to GitHub
2. Visit [share.streamlit.io](https://share.streamlit.io) and connect the repo
3. Set all `.env` variables as Streamlit secrets
4. Set the main file path to `src/finapp/gui/main.py`

**Note**: Streamlit Community Cloud provides ephemeral storage — use PostgreSQL for persistent portfolio data.

### Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | Anthropic API key (required) |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | Claude model for all agents |
| `DATABASE_URL` | `sqlite+aiosqlite:///./finapp.db` | Database connection string |
| `ALPHA_VANTAGE_API_KEY` | — | Alpha Vantage key (optional) |
| `NEWS_API_KEY` | — | NewsAPI key (optional) |
| `BRAVE_SEARCH_API_KEY` | — | Brave Search key (optional) |
| `APP_ENV` | `development` | Environment flag |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `CACHE_DIR` | `.cache` | Directory for market data cache |
| `DEFAULT_BENCHMARK` | `SPY` | Default comparison benchmark |
| `RISK_FREE_RATE_ANNUAL` | `0.05` | Risk-free rate for Sharpe ratio |

---

## Project Structure

```
Financial-AI-App/
├── openspec/                     # Spec Driven Development files
│   ├── project.yaml              # Root manifest — tech stack, coding standards
│   ├── requirements.yaml         # Functional + non-functional requirements
│   ├── architecture.yaml         # Layers, components, dependency rules
│   ├── agents.yaml               # AI agent definitions and contracts
│   ├── mcp.yaml                  # MCP server and tool specifications
│   ├── gui.yaml                  # UI pages, components, navigation
│   ├── data_models.yaml          # Entities, schemas, relationships
│   ├── guardrails.yaml           # Hard constraints — compliance, security, quality
│   └── fluid_requirements.yaml   # Extensible/adaptive requirements
│
├── src/finapp/
│   ├── config.py                 # All settings from environment variables
│   ├── domain/
│   │   ├── models/               # Portfolio, Account, Holding, Transaction, Goal, ...
│   │   ├── calculators/          # VaR, Sharpe, TWR, IRR, stress tests, FV projection
│   │   └── repositories/         # Abstract repository interfaces (ABCs)
│   ├── infrastructure/
│   │   ├── database.py           # SQLAlchemy async engine + session factory
│   │   ├── orm_models.py         # ORM table definitions
│   │   ├── repositories/         # SQLAlchemy repository implementations
│   │   └── cache/                # diskcache wrapper with domain TTL helpers
│   ├── mcp_servers/              # 6 FastMCP tool servers
│   ├── app/
│   │   ├── agents/               # 7 Claude agent classes
│   │   └── services/             # Portfolio, market data, risk, news services
│   └── gui/
│       ├── main.py               # Streamlit entry point
│       ├── components/           # Shared UI components (disclaimer, metrics, colors)
│       └── pages/                # Dashboard, Portfolio, AI Advisor, Market, Risk, News, Settings
│
├── tests/
│   ├── conftest.py
│   └── domain/                   # 35+ unit tests for all financial calculators
│
├── Notes/
│   ├── ClaudeWork_1.md           # Session 1: OpenSpec generation rationale
│   └── ClaudeWork_2.md           # Session 2: Application build documentation
│
├── pyproject.toml                # Project dependencies and tool config
├── .env.example                  # Environment variable template
├── CLAUDE.md                     # Instructions for Claude Code (AI development guide)
└── README.md
```

---

## Future Enhancements

### v0.2 — Data Quality & Persistence

- **Daily portfolio snapshots** — Store portfolio value daily to enable a true historical value chart (currently uses single-ticker price as proxy)
- **Persistent watchlist** — Domain models and ORM tables already defined; wire up to the Settings and Market pages
- **Alembic migrations** — Schema version control for safe database upgrades
- **Price alert evaluation** — Background loop to check active `PriceAlert` records against live quotes and surface triggered alerts in the UI

### v0.3 — Enhanced AI Intelligence

- **Agent memory persistence** — Store conversation history in the database so agents remember prior discussions across sessions
- **FinBERT sentiment** — Replace the keyword-based sentiment scorer with a fine-tuned financial language model for more accurate article scoring
- **Multi-step agent chaining UI** — Show intermediate agent handoffs in the chat (e.g., "Routing to Risk Analyst → Market Researcher")
- **Agent evaluation metrics** — Log whether responses included the required disclaimer, were on-topic, and required tool use — for quality monitoring
- **Earnings calendar integration** — Surface upcoming earnings dates for portfolio holdings in the Dashboard and News pages

### v0.4 — Production Readiness

- **Docker Compose stack** — Separate containers for Streamlit UI, agent orchestration, and each MCP server
- **PostgreSQL + Redis** — Production database and Redis-backed cache (swap `DATABASE_URL` and cache backend)
- **User authentication** — Local password auth or OAuth 2.0 (Google/GitHub) for multi-user support
- **HTTPS + reverse proxy** — Nginx/Caddy in front of Streamlit for production TLS
- **Secrets management** — HashiCorp Vault or AWS Secrets Manager instead of `.env` files
- **CI/CD pipeline** — GitHub Actions: lint → type check → test → Docker build → deploy

### v0.5 — Advanced Portfolio Features

- **CSV portfolio import** — Parse brokerage export files (Fidelity, Schwab, IBKR formats) to bulk-load holdings
- **Tax-loss harvesting scanner** — Identify positions with unrealised losses and suggest similar replacement securities to maintain market exposure while harvesting the loss
- **Rebalancing engine** — Calculate exact trades needed to restore target allocation, with tax-impact preview
- **Dividend tracking** — Automatically record dividend income from yfinance corporate actions data
- **Options tracking** — Add support for option positions (calls, puts) with greeks display
- **Crypto portfolio** — Dedicated crypto asset class support with on-chain data providers

### v0.6 — Advanced AI Features

- **Voice interface** — Whisper speech-to-text for voice queries; text-to-speech for responses
- **Scheduled AI digest** — Daily/weekly portfolio summary email generated by the News Sentinel and Portfolio Advisor agents
- **PDF report generation** — AI-narrated performance reports with charts, generated on demand
- **Anomaly detection** — ML model to flag unusual portfolio movements or news events that historically preceded significant price moves
- **Backtesting** — Simulate how proposed allocation changes would have performed historically

### v0.7 — React Frontend Migration

- Replace Streamlit with a React + TypeScript frontend for richer interactivity
- FastAPI backend serving the application layer as a REST/WebSocket API
- Real-time price streaming via WebSocket connections
- Mobile-responsive design
- The architecture is already prepared for this — the application layer has no Streamlit imports

---

## Contributing

This project was built using [Spec Driven Development](Notes/ClaudeWork_1.md). Before making changes:

1. Review the relevant OpenSpec file in [`openspec/`](openspec/)
2. Read [`CLAUDE.md`](CLAUDE.md) for development conventions
3. Consult [`openspec/guardrails.yaml`](openspec/guardrails.yaml) — these constraints are non-negotiable
4. Run the test suite: `uv run pytest`

---

## Disclaimer

> FinApp is for **informational and educational purposes only**. Nothing in this application constitutes financial advice, investment advice, or a recommendation to buy or sell any security. Always consult a licensed financial advisor before making investment decisions. Past performance does not guarantee future results.

---

*Built with [Claude Code](https://claude.ai/claude-code) using Spec Driven Development and the OpenSpec standard.*
