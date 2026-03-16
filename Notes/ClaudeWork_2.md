# FinApp — Software Build Session Record

**Date:** 2026-03-15
**Project:** FinApp — AI-Enabled Financial Application
**Claude Model:** claude-sonnet-4-6
**Session:** ClaudeWork_2 — Full application build from OpenSpec

---

## Table of Contents

1. [Build Summary](#1-build-summary)
2. [Complete File Manifest](#2-complete-file-manifest)
3. [Architecture Implemented](#3-architecture-implemented)
4. [Layer-by-Layer Build Notes](#4-layer-by-layer-build-notes)
5. [Key Design Decisions](#5-key-design-decisions)
6. [Guardrails Compliance](#6-guardrails-compliance)
7. [How to Run](#7-how-to-run)
8. [How to Test](#8-how-to-test)
9. [What Comes Next](#9-what-comes-next)

---

## 1. Build Summary

This session built the complete FinApp application from the 8 OpenSpec files created in ClaudeWork_1. The application is fully functional as a development-mode single-process Streamlit application.

**Files Created:** 45+ source files across 5 architectural layers
**Lines of Code:** ~4,000+ lines
**Test Coverage Target:** 80% (domain calculators fully covered)
**Guardrails Enforced:** All GRD-* rules from `openspec/guardrails.yaml`

### What Was Built

| Layer | Files | Description |
|-------|-------|-------------|
| Project Setup | 4 | pyproject.toml, .env.example, CLAUDE.md, directory structure |
| Config | 1 | pydantic-settings config.py |
| Domain | 10 | 7 models + 2 calculators + 1 repository interface file |
| Infrastructure | 4 | SQLAlchemy engine, ORM models, repositories, disk cache |
| MCP Servers | 6 | market-data, news, portfolio, calculator, search, export |
| AI Agents | 8 | base + orchestrator + 6 specialist agents |
| App Services | 4 | portfolio, market-data, risk, news |
| GUI | 9 | main.py + 7 pages + shared components |
| Tests | 4 | risk calculator, performance calculator, domain models, conftest |

---

## 2. Complete File Manifest

```
Financial-AI-App/
├── pyproject.toml                    # Project metadata + all dependencies
├── .env.example                      # Template for API keys
├── CLAUDE.md                         # Instructions for future Claude Code sessions
│
├── src/finapp/
│   ├── config.py                     # Pydantic-settings: all config from .env
│   │
│   ├── domain/                       # Pure business logic (no external I/O)
│   │   ├── models/
│   │   │   ├── portfolio.py          # Portfolio aggregate root
│   │   │   ├── account.py            # Investment account model
│   │   │   ├── holding.py            # Position + TaxLot models
│   │   │   ├── transaction.py        # Immutable transaction record
│   │   │   ├── watchlist.py          # WatchlistItem + PriceAlert
│   │   │   ├── goal.py               # FinancialGoal with progress tracking
│   │   │   └── market.py             # Transient: Quote, OHLCV, Fundamentals, News
│   │   ├── calculators/
│   │   │   ├── risk_calculator.py    # VaR, Sharpe, Beta, Correlation, Stress Test
│   │   │   └── performance_calculator.py  # TWR, IRR, Alpha, FV Projection, Tax
│   │   └── repositories/
│   │       └── interfaces.py         # ABCs: IPortfolio, IHolding, ITransaction, etc.
│   │
│   ├── infrastructure/               # Database + cache (implements domain interfaces)
│   │   ├── database.py               # SQLAlchemy async engine + get_session()
│   │   ├── orm_models.py             # SQLAlchemy ORM table definitions
│   │   ├── repositories/
│   │   │   └── portfolio_repository.py  # PortfolioRepo, HoldingRepo, TransactionRepo
│   │   └── cache/
│   │       └── market_data_cache.py  # diskcache wrapper with domain-specific TTLs
│   │
│   ├── mcp_servers/                  # 6 MCP servers (tool endpoints for AI agents)
│   │   ├── market_data_server.py     # yfinance quotes, OHLCV, fundamentals, technicals
│   │   ├── news_server.py            # NewsAPI + SEC EDGAR + keyword sentiment
│   │   ├── portfolio_server.py       # Portfolio CRUD over SQLite via repositories
│   │   ├── calculator_server.py      # VaR, Sharpe, stress test, IRR, FV, tax, optimize
│   │   ├── search_server.py          # Brave Search API for Market Researcher agent
│   │   └── export_server.py          # CSV + PDF report generation
│   │
│   ├── app/                          # Application layer (no streamlit imports)
│   │   ├── agents/
│   │   │   ├── base_agent.py         # Streaming base + tool-use loop + disclaimer
│   │   │   ├── orchestrator_agent.py # Intent classification + agent routing
│   │   │   ├── portfolio_advisor_agent.py
│   │   │   ├── risk_analyst_agent.py
│   │   │   ├── market_researcher_agent.py
│   │   │   ├── news_sentinel_agent.py
│   │   │   ├── financial_planner_agent.py
│   │   │   └── trade_reviewer_agent.py
│   │   └── services/
│   │       ├── portfolio_service.py  # Portfolio CRUD use-cases
│   │       ├── market_data_service.py # Price fetching + historical returns
│   │       ├── risk_service.py        # Risk metrics + stress testing
│   │       └── news_service.py        # News for portfolio holdings
│   │
│   └── gui/                          # Streamlit GUI (no business logic)
│       ├── main.py                   # Entry point (Dashboard + DB init)
│       ├── components/
│       │   └── shared.py             # Disclaimer banner, color helpers, metric_row
│       └── pages/
│           ├── dashboard.py          # KPIs + charts + holdings table + news preview
│           ├── portfolio.py          # Holdings mgmt + Add Holding form + Transactions
│           ├── ai_advisor.py         # Streaming chat with all agents
│           ├── market.py             # Candlestick charts + technicals + watchlist
│           ├── risk.py               # VaR + correlation heatmap + stress test UI
│           ├── news.py               # News feed with sentiment badges
│           └── settings.py           # API key mgmt + portfolio config + preferences
│
└── tests/
    ├── conftest.py                   # Session fixtures + env setup
    └── domain/
        ├── test_risk_calculator.py   # 20+ tests: VaR, Sharpe, Beta, Correlation, Stress
        ├── test_performance_calculator.py  # 15+ tests: TWR, IRR, Alpha, FV
        └── test_domain_models.py     # Holding + Transaction model tests
```

---

## 3. Architecture Implemented

The application follows the layered architecture defined in `openspec/architecture.yaml`:

```
┌─────────────────────────────────────────┐
│  Presentation Layer (Streamlit)          │  gui/pages/*.py
│  NO business logic, NO database access  │
├─────────────────────────────────────────┤
│  Application Layer                       │  app/agents/ + app/services/
│  Use-cases, orchestration, AI agents     │  (NO streamlit imports)
├─────────────────────────────────────────┤
│  Domain Layer                            │  domain/models/ + domain/calculators/
│  Pure Python, NO external dependencies  │  (only stdlib + numpy/scipy)
├─────────────────────────────────────────┤
│  Infrastructure Layer                    │  infrastructure/
│  SQLAlchemy + diskcache                 │  (implements domain interfaces)
├─────────────────────────────────────────┤
│  MCP Server Layer                        │  mcp_servers/
│  Tool endpoints called by AI agents     │  (runs as separate concern)
└─────────────────────────────────────────┘
```

### Dependency Flow

```
GUI → App Services → Domain Models
GUI → App Agents → MCP Servers → External APIs (yfinance, NewsAPI, Brave)
App Agents → Domain Calculators (pure functions)
MCP Servers → Infrastructure (repositories, cache)
Infrastructure → Domain (models + repository interfaces)
```

---

## 4. Layer-by-Layer Build Notes

### Domain Layer

**Models** — All use Pydantic v2 with `computed_field` for derived properties:
- `Portfolio`: aggregate root; `total_value`, `asset_allocation` computed from accounts
- `Holding`: `current_price` is injected externally (from MarketDataService); `gain_loss`, `is_long_term` computed
- `Transaction`: frozen (`model_config = {"frozen": True}`) — immutable after creation per spec
- `TaxLot`: linked to holding + transaction for accurate cost basis tracking
- `Market.py`: transient models (MarketQuote, OHLCVBar, etc.) — cached, not persisted

**Calculators** — All functions are pure (no side effects):
- `risk_calculator.py`: VaR (historical simulation), Sharpe/Sortino, Beta, Correlation Matrix, Stress Tests
- `performance_calculator.py`: TWR, IRR (Newton-Raphson), Alpha (Jensen's), FV Projection (3 scenarios), Tax Impact, Portfolio Optimization (Monte Carlo)

Key decision: stress test uses pre-defined historical crash drawdowns by asset class rather than fetching live historical data. This makes stress testing fast, deterministic, and available offline.

### Infrastructure Layer

**Database**: SQLAlchemy 2.0 async pattern with `AsyncSession`. All ORM models in `orm_models.py` use the new `Mapped[]` type annotation style. The `get_session()` async context manager handles commit/rollback automatically.

**Repository Pattern**: Three repositories implement the domain interfaces:
- `PortfolioRepository` — eagerly loads accounts → holdings → tax_lots via `selectinload`
- `HoldingRepository` — supports filtering by `include_closed`
- `TransactionRepository` — append-only; no UPDATE or DELETE operations

**Cache**: `diskcache` provides persistence between Streamlit reruns. TTLs from config:
- Quotes: 5 min | Historical: 1 hr | Fundamentals: 24 hr | News: 30 min

### MCP Servers

All 6 servers use `FastMCP` from the `mcp` Python SDK and run via `stdio` transport.

| Server | Data Source | Key Design |
|--------|-------------|------------|
| market-data-mcp | yfinance (primary) | Cache-aside pattern; Alpha Vantage key optional |
| news-mcp | NewsAPI + SEC EDGAR | Keyword sentiment scorer; graceful fallback if no API key |
| portfolio-mcp | SQLite via repositories | Validates all inputs before persistence |
| calculator-mcp | numpy/scipy (internal) | Wraps domain calculators; adds 3-scenario FV |
| search-mcp | Brave Search API | Returns empty result with instructions if no key |
| export-mcp | reportlab (PDF) / csv | Falls back to text report if reportlab unavailable |

**Sentiment Analysis**: A keyword-based scorer in `news_server.py` using positive/negative word lists provides instant sentiment without an additional API. Accurate enough for news triage; can be replaced with a transformer model later.

### AI Agents

All agents extend `BaseAgent` which provides:
1. **Streaming tool-use loop** — up to 5 rounds of tool calls before returning
2. **Mandatory disclaimer injection** — defined in `GLOBAL_SYSTEM_PROMPT_PREFIX`
3. **`_dispatch_tool()` pattern** — each agent overrides this to route tool names to MCP functions

**OrchestratorAgent**: Uses keyword-based intent classification (`_classify_intent`) to route to the appropriate specialist. For queries matching "portfolio", "risk", "market", "news", "planner", or "trade" keywords, it instantiates the right specialist agent and delegates the full stream.

**Anthropic SDK usage**:
```python
async with self._client.messages.stream(
    model=settings.anthropic_model,
    tools=self.tools,
    ...
) as stream:
    async for event in stream:
        # Yield text tokens, collect tool_use blocks
```

The tool-use loop automatically feeds tool results back until Claude generates a pure text response.

### GUI

**Streamlit patterns used**:
- `st.session_state` for conversation history, watchlist, and settings
- `asyncio.run()` to call async services from sync Streamlit callbacks
- `st.write_stream()` for streaming AI responses
- `st.spinner()` for all data fetch operations (GRD-CQ-003)
- `st.form()` for add-holding and API key inputs

**Page routing**: Uses Streamlit's multipage app via `st.page_link()` in the sidebar. Each page file has its own `render_*()` function.

---

## 5. Key Design Decisions

### D1: yfinance as Primary Market Data Source
**Decision**: Use `yfinance` (Yahoo Finance) as the primary market data source, not Alpha Vantage.
**Rationale**: yfinance requires no API key, has no rate limits for personal use, and provides quotes, historical OHLCV, fundamentals, and fast_info. Alpha Vantage is retained as a future upgrade path.
**Trade-off**: yfinance is unofficial (no SLA). Alpha Vantage key can be added to `.env` for production.

### D2: Keyword Sentiment vs. ML Model
**Decision**: Implement keyword-based sentiment scoring in `news_server.py`.
**Rationale**: Zero latency, no additional API, no GPU required, deterministic. A transformer-based model (e.g., FinBERT) can replace this later via the `get_sentiment_score` tool without changing the agent interface.

### D3: asyncio.run() in Streamlit
**Decision**: Call async services via `asyncio.run()` in Streamlit pages.
**Rationale**: Streamlit's sync execution model doesn't natively support async. `asyncio.run()` creates a new event loop per call. For production, consider `streamlit-asyncio` or restructuring with `st.cache_data` + thread executors.

### D4: Monte Carlo Portfolio Optimization
**Decision**: Use Monte Carlo simulation (5,000 random portfolios) for `optimize_weights`, not scipy optimization.
**Rationale**: More robust to non-convex constraint landscapes, easier to implement, and provides a natural visualization of the efficient frontier. scipy `minimize` can be added for precision later.

### D5: Session State for Watchlist
**Decision**: Watchlist stored in Streamlit `session_state`, not the database.
**Rationale**: Lower friction for v0.1. The `WatchlistItem` and `PriceAlert` domain models + ORM tables are fully defined and ready for persistent watchlist in v0.2.

### D6: Single-User Architecture
**Decision**: Use a hardcoded `DEFAULT_USER_ID = "local_user"` for v0.1.
**Rationale**: The spec targets a single-user local app. Multi-user support requires an auth layer (defined in `fluid_requirements.yaml` as a future capability). All repositories accept `user_id` as a parameter, so multi-user support is a configuration change, not an architectural refactor.

---

## 6. Guardrails Compliance

Every guardrail from `openspec/guardrails.yaml` was enforced during build:

| Guardrail ID | Rule | Implementation |
|-------------|------|----------------|
| GRD-FC-001 | Mandatory disclaimer in all AI responses | `GLOBAL_SYSTEM_PROMPT_PREFIX` in `base_agent.py`; `show_disclaimer_banner()` on AI page |
| GRD-FC-002 | No unlicensed investment advice | Agent system prompts use "consider", "historically", "analysis suggests" language |
| GRD-FC-003 | Tax disclaimer | `calculator_server.py: tool_calculate_tax_impact` appends disclaimer to every response |
| GRD-FC-004 | Three projection scenarios | `tool_project_future_value` always returns conservative, base, and optimistic scenarios |
| GRD-SEC-001 | No hardcoded API keys | All keys via `pydantic-settings` reading from `.env` |
| GRD-SEC-002 | No SQL injection | SQLAlchemy ORM throughout; no raw SQL anywhere |
| GRD-SEC-003 | Input validation | `portfolio_service.py` validates ticker, quantity, date before persistence |
| GRD-SEC-004 | Data privacy | Portfolio data stays on local machine; no cloud sync in v1 |
| GRD-SEC-005 | No external data leakage | MCP servers send only tickers to external APIs, never quantities or values |
| GRD-CQ-001 | No bare exceptions | All `except` clauses catch specific types (ValueError, httpx.HTTPStatusError, etc.) |
| GRD-CQ-002 | Financial math precision | Decimal throughout domain; numpy for vectorised calculations |
| GRD-CQ-003 | No blocking Streamlit | All data fetches wrapped in `st.spinner()` |
| GRD-CQ-004 | Tests for calculators | 35+ test cases across 3 test files covering all calculator functions |
| GRD-CQ-005 | Type annotations | All public functions have full type annotations |
| GRD-ARCH-001 | Layer isolation | No streamlit imports in app/ or domain/; no direct DB access in GUI |
| GRD-ARCH-002 | Repository pattern | All DB access through `PortfolioRepository`, `HoldingRepository`, `TransactionRepository` |
| GRD-ARCH-003 | MCP tool contracts | Tool parameters and return types match `openspec/mcp.yaml` exactly |
| GRD-OPS-001 | Rate limiting | Cache TTLs prevent excessive API calls; diskcache persists between sessions |
| GRD-OPS-002 | Graceful degradation | All MCP servers return informational messages, not crashes, when APIs are unavailable |
| GRD-OPS-003 | Data staleness | `staleness_warning()` shown when cache age > 15 minutes; timestamps shown on all data |

---

## 7. How to Run

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager

### Setup

```bash
# 1. Install dependencies
cd /home/rsingh/Learn/Financial-AI-App
uv sync

# 2. Configure API keys
cp .env.example .env
# Edit .env and add at minimum:
#   ANTHROPIC_API_KEY=sk-ant-...
# Other keys are optional (app degrades gracefully without them)

# 3. Start the application
uv run streamlit run src/finapp/gui/main.py
```

The application will:
1. Create the SQLite database (`finapp.db`) on first run
2. Open in your browser at `http://localhost:8501`

### First Steps

1. Go to **Settings** → **API Keys** and enter your Anthropic key
2. Go to **Portfolio** → **Add Holding** to add your first positions
3. Return to **Dashboard** to see your portfolio overview
4. Visit **AI Advisor** to chat with the financial agents

### Required API Keys

| Key | Required | Purpose | Free Tier |
|-----|----------|---------|-----------|
| `ANTHROPIC_API_KEY` | **Yes** | All AI agents | Pay-as-you-go |
| `ALPHA_VANTAGE_API_KEY` | No | Enhanced market data | 5 req/min |
| `NEWS_API_KEY` | No | Financial news | 100 req/day |
| `BRAVE_SEARCH_API_KEY` | No | Web search in agents | 2000 req/month |

Without optional keys, the app uses yfinance for market data and shows "News API not configured" messages.

---

## 8. How to Test

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run only calculator tests
uv run pytest tests/domain/test_risk_calculator.py -v

# Run with coverage report
uv run pytest --cov=src/finapp --cov-report=html

# Lint and format
uv run ruff check src/
uv run ruff format src/

# Type checking
uv run mypy src/finapp/domain/ src/finapp/app/
```

### Test Coverage

| Module | Tests | Key Scenarios |
|--------|-------|---------------|
| `risk_calculator.py` | 20+ | VaR empty/zero/scaling, Sharpe edge cases, Beta identical series, Correlation symmetry/bounds, all stress scenarios |
| `performance_calculator.py` | 15+ | TWR single/multi period, IRR convergence/no-sign-change, Alpha benchmark parity, FV monotonic growth |
| `domain/models` | 10+ | Holding computed properties, Transaction immutability, gain/loss calculations |

---

## 9. What Comes Next

Based on `openspec/fluid_requirements.yaml`, the natural next iterations are:

### v0.2 — Data Quality & Persistence
- [ ] Daily portfolio value snapshots (enables proper historical value chart)
- [ ] Persistent watchlist in database (domain models already defined)
- [ ] Alembic database migrations setup
- [ ] Price alert evaluation loop (models defined, trigger logic needed)

### v0.3 — Enhanced AI Agents
- [ ] Memory persistence for agents (conversation history across sessions)
- [ ] FinBERT or similar for accurate news sentiment scoring
- [ ] Agent evaluation metrics (track which responses include disclaimer, are relevant)
- [ ] Multi-step agent chaining UI (show intermediate steps in chat)

### v0.4 — Production Readiness
- [ ] Docker containerization (Dockerfile + docker-compose)
- [ ] PostgreSQL migration (DATABASE_URL swap in `.env`)
- [ ] Redis cache backend (swap diskcache for Redis)
- [ ] User authentication (local password or OAuth)
- [ ] HTTPS + proper secrets management

### v0.5 — Advanced Features
- [ ] Portfolio import via CSV (brokerage export format)
- [ ] Tax-loss harvesting scanner
- [ ] Scheduled news digest (daily email/notification)
- [ ] Custom benchmark support
- [ ] React frontend migration (from Streamlit)

---

## Appendix: Technology Versions

| Library | Version | Purpose |
|---------|---------|---------|
| streamlit | ≥1.42.0 | GUI framework |
| anthropic | ≥0.49.0 | Claude AI API client |
| mcp | ≥1.5.0 | MCP server SDK |
| sqlalchemy | ≥2.0.0 | Async ORM |
| yfinance | ≥0.2.55 | Market data (free, no key) |
| pydantic | ≥2.10.0 | Data validation + settings |
| pydantic-settings | ≥2.7.0 | .env configuration |
| numpy | ≥1.26.0 | Vectorised financial math |
| scipy | ≥1.12.0 | Statistical functions |
| plotly | ≥5.24.0 | Interactive charts |
| diskcache | ≥5.6.0 | Persistent disk cache |
| httpx | ≥0.27.0 | Async HTTP client |
| reportlab | ≥4.2.0 | PDF report generation |
| pytest | ≥8.0.0 | Test framework |
| ruff | ≥0.8.0 | Linting + formatting |
| mypy | ≥1.11.0 | Type checking |
