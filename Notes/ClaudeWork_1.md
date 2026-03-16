# Spec Driven Development with OpenSpec: AI-Enabled Financial Application

**Date:** 2026-03-15
**Project:** FinApp — AI-Enabled Financial Application
**Claude Model:** claude-sonnet-4-6

---

## Table of Contents

1. [What is Spec Driven Development (SDD)?](#1-what-is-spec-driven-development)
2. [OpenSpec vs Interactive Prompts: A Comparative Analysis](#2-openspec-vs-interactive-prompts)
3. [OpenSpec File Structure for SDD](#3-openspec-file-structure)
4. [Financial Application Analysis & Capabilities](#4-financial-application-analysis)
5. [Artifacts Generated](#5-artifacts-generated)
6. [Reasoning & Design Decisions](#6-reasoning--design-decisions)

---

## 1. What is Spec Driven Development?

**Spec Driven Development (SDD)** is a software development methodology where formal, machine-readable specification files serve as the single source of truth for a software system — before any code is written. These specifications define *what* the system should do, *how* it should behave, *what constraints* it must respect, and *how* it can evolve — independent of any particular implementation.

### The OpenSpec Philosophy

OpenSpec is a structured specification standard that borrows principles from:

- **OpenAPI** (REST API contracts) — structured, versioned, schema-driven definitions
- **AsyncAPI** (event-driven systems) — message-based interaction modeling
- **Architecture Decision Records (ADRs)** — capturing the *why* behind design choices
- **Behavior-Driven Development (BDD)** — specifying behavior from a user perspective

OpenSpec goes beyond API contracts to cover the *entire software system*: architecture, agents, data models, UI behavior, business rules, guardrails, and extensibility boundaries. It uses YAML/JSON as the primary format because:

- Human-readable and editable
- Version-controllable (diffs are meaningful)
- Machine-parseable (AI agents can reason over them)
- Tooling-agnostic (no lock-in to specific IDEs or frameworks)

### Core Principles of SDD with OpenSpec

| Principle | Description |
|-----------|-------------|
| **Specification First** | Write specs before code; code is an artifact of the spec |
| **Single Source of Truth** | All stakeholders (human & AI) reference the same spec files |
| **Versioned Contracts** | Specs are versioned; changes are explicit and traceable |
| **Separation of Concerns** | Requirements, architecture, guardrails, and fluid requirements are separate files |
| **Progressive Elaboration** | Specs can start high-level and be refined iteratively |
| **Machine + Human Readable** | Specs are interpretable by both humans and AI code generators |

---

## 2. OpenSpec vs Interactive Prompts: A Comparative Analysis

### The Interactive Prompt Approach (Status Quo)

When developers use Claude Code through conversational prompts without formal specs, a typical session looks like:

```
User: "Build me a portfolio tracker"
Claude: [generates code]
User: "Actually add authentication"
Claude: [adds auth, possibly breaking patterns already established]
User: "The risk calculation is wrong, use VaR not standard deviation"
Claude: [fixes, may introduce inconsistencies]
User: "Why is the agent not using the right data source?"
Claude: [cannot recall prior decisions from scratch]
```

This creates a **context entropy problem** — each session starts fresh, decisions are lost, and the codebase accumulates contradictions.

### Effectiveness Comparison

| Dimension | Interactive Prompts | Formal OpenSpec (SDD) |
|-----------|--------------------|-----------------------|
| **Context Retention** | Lost between sessions | Persistent in spec files — always available |
| **Consistency** | Degrades over time | Enforced by spec constraints |
| **Ambiguity** | High — resolved ad hoc | Low — disambiguated in spec |
| **Change Management** | Implicit, hard to trace | Explicit spec version diffs |
| **Onboarding** | Requires re-explaining context | New AI session reads the spec |
| **Scope Creep** | Common — no boundary enforcement | Prevented by guardrails spec |
| **Code Quality** | Variable — depends on prompt quality | High — specs encode best practices |
| **Testability** | Ad hoc | Acceptance criteria defined in spec |
| **Scalability** | Breaks down for complex systems | Scales linearly with spec completeness |
| **Reproducibility** | Low — same prompt → different output | High — spec pins decisions |
| **Collaboration** | Single person loop | Multi-stakeholder review of specs |
| **Regulatory Compliance** | Hard to audit | Guardrails spec is auditable |

### When Interactive Prompts Work Well

- Prototyping/exploration (< 2 hours of work)
- Single-function implementations
- Learning and experimentation
- Ad hoc debugging assistance

### When OpenSpec (SDD) is Dramatically Superior

- Applications > 1,000 lines of code
- Multi-agent systems with complex interactions
- Applications requiring regulatory compliance
- Team environments with multiple developers
- Long-lived projects (months to years)
- AI-generated code that must meet quality gates
- **Financial applications** (exactly this use case)

### Quantitative Impact Estimate

Based on the nature of this financial application (multi-agent, MCP servers, GUI, data pipelines):

- **Without SDD**: Expect 40-60% rework due to inconsistency, 3-5x more prompting sessions, high probability of architectural violations
- **With SDD**: First-pass code generation aligns with architecture 80-90% of the time, changes are isolated and traceable, Claude Code can regenerate any module independently while preserving system coherence

---

## 3. OpenSpec File Structure for SDD

### Recommended File Hierarchy

```
project/
├── openspec/
│   ├── project.yaml              # Root manifest: name, version, tech stack, global metadata
│   ├── requirements.yaml         # Functional + non-functional requirements
│   ├── architecture.yaml         # System components, layers, dependencies, patterns
│   ├── agents.yaml               # AI Agent definitions: goals, tools, memory, handoffs
│   ├── mcp.yaml                  # MCP servers, tools, resources, prompts
│   ├── gui.yaml                  # UI pages, components, navigation, state
│   ├── data_models.yaml          # Entities, schemas, relationships, storage
│   ├── guardrails.yaml           # Hard constraints, forbidden patterns, compliance rules
│   └── fluid_requirements.yaml   # Extensible/adaptive requirements, feature flags
├── diagrams.md                   # Mermaid architecture + HLD diagrams
└── CLAUDE.md                     # Instructions for Claude Code on how to use the specs
```

### Role of Each File

#### `project.yaml` — The Root Manifest
The entry point for Claude Code. Contains project identity, tech stack pinning, coding standards, and references to all other spec files. Claude Code should read this first before generating any code.

#### `requirements.yaml` — What the System Must Do
Structured as:
- **Epics** → **Stories** → **Acceptance Criteria**
- Each requirement has: ID, priority, status, dependencies
- Acceptance criteria are written as testable statements
- Non-functional requirements (performance, security, availability) have measurable thresholds

#### `architecture.yaml` — How the System is Built
Defines:
- Layers (presentation, business logic, data, infrastructure)
- Component catalog with responsibilities and interfaces
- Dependency rules (what can call what)
- Technology decisions and rationale
- Integration patterns (event-driven, request-response, streaming)

#### `agents.yaml` — AI Agent Contracts
For each agent:
- Goal and persona
- Tools available (mapped to MCP tools)
- Memory type (short-term, long-term, episodic)
- Input/output contracts
- Handoff protocols to other agents
- Evaluation criteria

#### `mcp.yaml` — MCP Server Definitions
For each MCP server:
- Server name, version, transport
- Resources (data sources it exposes)
- Tools (functions it provides)
- Prompts (reusable prompt templates)
- Authentication requirements

#### `gui.yaml` — UI Specification
- Page catalog with routes and layouts
- Component hierarchy
- State management rules
- Navigation flows
- Accessibility requirements
- Theming constraints

#### `guardrails.yaml` — Hard Constraints
The most critical file for a financial application:
- Regulatory compliance rules (SEC, FINRA, GDPR)
- Financial advice disclaimers (mandatory)
- Data validation boundaries
- Security constraints (no credentials in code, encryption at rest)
- Forbidden patterns (no raw SQL concatenation, no storing API keys in plaintext)
- Rate limiting and abuse prevention

#### `fluid_requirements.yaml` — Extensible Requirements
For requirements that will evolve:
- Feature flags and their conditions
- Plugin/extension points in the architecture
- Configuration-driven behaviors
- A/B testing specifications
- Future-proof interface definitions
- Versioning strategy for breaking changes

---

## 4. Financial Application Analysis & Capabilities

### Initial Assessment

The user has stated the requirements are not fully clear. This is actually ideal for SDD — we capture what is known, mark uncertain areas with `status: exploratory`, and define extensibility points where requirements will solidify over time.

### Core Domain Analysis

A modern AI-enabled financial application spans these domains:

#### Domain 1: Portfolio Management
- Track holdings across asset classes (equities, bonds, ETFs, crypto, alternatives)
- Real-time and historical valuation
- Performance attribution (what drove returns)
- Benchmark comparison (vs S&P 500, custom indices)
- Tax lot tracking for cost basis

#### Domain 2: Market Intelligence
- Real-time price feeds and quotes
- Technical analysis indicators (RSI, MACD, Bollinger Bands)
- Fundamental data (P/E, earnings, revenue)
- Economic indicators (CPI, unemployment, Fed rates)
- Earnings calendar and corporate events

#### Domain 3: AI-Powered Advisory
- Personalized investment recommendations
- Portfolio rebalancing suggestions
- Risk-adjusted return optimization
- Goal-based financial planning
- Natural language Q&A about portfolio

#### Domain 4: Risk Management
- Value at Risk (VaR) calculations
- Portfolio concentration analysis
- Correlation and diversification scoring
- Stress testing and scenario analysis
- Drawdown monitoring and alerts

#### Domain 5: News & Sentiment Analysis
- Financial news aggregation
- Sentiment scoring (positive/negative/neutral)
- Entity extraction (companies, people, events)
- Impact assessment on holdings
- Trend detection

#### Domain 6: Personal Finance
- Budget tracking and categorization
- Cash flow forecasting
- Expense analysis
- Savings goal tracking
- Net worth calculation

#### Domain 7: Tax & Compliance
- Tax-loss harvesting opportunities
- Capital gains/loss reporting
- Wash sale rule compliance
- Tax efficiency scoring
- IRS form data export (informational only)

#### Domain 8: Reporting & Visualization
- Interactive portfolio dashboards
- Performance charts (time-series, heatmaps)
- Risk exposure visualizations
- Custom report generation
- PDF/CSV export

### AI Agents Identified

| Agent | Primary Goal | Key Tools |
|-------|-------------|-----------|
| **Portfolio Advisor** | Provide personalized investment recommendations | Portfolio data, market data, user profile |
| **Risk Analyst** | Assess and quantify portfolio risk | VaR calculator, correlation engine, stress test |
| **Market Researcher** | Research specific securities or sectors | News API, fundamental data, technical analysis |
| **News Sentinel** | Monitor and summarize relevant financial news | News aggregator, sentiment analyzer, NLP |
| **Financial Planner** | Create and monitor long-term financial plans | Goal tracker, projection calculator, budget |
| **Trade Reviewer** | Review and validate proposed trades | Compliance checker, risk assessor, market data |
| **Orchestrator** | Route user queries to appropriate agents | All agents, user context |

### MCP Servers Identified

| MCP Server | Purpose | External APIs |
|-----------|---------|---------------|
| **market-data-mcp** | Real-time and historical market data | Yahoo Finance, Alpha Vantage, Polygon.io |
| **news-mcp** | Financial news and sentiment | NewsAPI, FinViz, SEC EDGAR |
| **portfolio-mcp** | Portfolio CRUD, valuation, performance | Internal SQLite/PostgreSQL |
| **calculator-mcp** | Financial calculations (VaR, IRR, NPV) | Internal computation engine |
| **search-mcp** | Web search for research | Brave Search or DuckDuckGo |
| **export-mcp** | Report generation and file export | Internal PDF/CSV generators |

### Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Language | Python 3.12+ | Ecosystem for finance + AI |
| Package Manager | uv | Fast, modern Python package management |
| GUI | Streamlit | Rapid data app development, built-in charting |
| AI Framework | Claude API + Anthropic SDK | Powerful reasoning, tool use, streaming |
| MCP Protocol | MCP Python SDK | Standard tool integration layer |
| Database | SQLite (dev) / PostgreSQL (prod) | Simple start, enterprise upgrade path |
| Data Processing | pandas, polars | DataFrames for financial data |
| Visualization | Plotly, Altair | Interactive charts in Streamlit |
| Financial Math | numpy, scipy, quantlib | Quantitative calculations |
| HTTP Client | httpx | Async HTTP for API calls |
| Config | pydantic-settings | Type-safe configuration |
| Testing | pytest + hypothesis | Property-based testing for financial logic |
| Secrets | python-dotenv | Local secrets management |

---

## 5. Artifacts Generated

The following OpenSpec files have been created in the `openspec/` directory:

| File | Purpose |
|------|---------|
| [openspec/project.yaml](openspec/project.yaml) | Root manifest and global metadata |
| [openspec/requirements.yaml](openspec/requirements.yaml) | Functional and non-functional requirements |
| [openspec/architecture.yaml](openspec/architecture.yaml) | System architecture and component catalog |
| [openspec/agents.yaml](openspec/agents.yaml) | AI Agent definitions and contracts |
| [openspec/mcp.yaml](openspec/mcp.yaml) | MCP server and tool specifications |
| [openspec/gui.yaml](openspec/gui.yaml) | GUI pages, components, and navigation |
| [openspec/guardrails.yaml](openspec/guardrails.yaml) | Hard constraints and compliance rules |
| [openspec/data_models.yaml](openspec/data_models.yaml) | Data entities, schemas, and relationships |
| [openspec/fluid_requirements.yaml](openspec/fluid_requirements.yaml) | Extensible and adaptive requirements |
| [diagrams.md](diagrams.md) | Architecture and HLD diagrams in Mermaid |

---

## 6. Reasoning & Design Decisions

### Why Separate Guardrails from Requirements?

Financial applications have a unique characteristic: **some constraints are non-negotiable regardless of business requirements**. Regulatory compliance (SEC regulations, FINRA rules), data security (PCI-DSS adjacent), and financial advice disclaimers cannot be traded off against features. Separating `guardrails.yaml` from `requirements.yaml` ensures Claude Code treats them with different priority levels — guardrails are NEVER violated, requirements are SHOULD/MUST with negotiable priority.

### Why Multiple MCP Servers Instead of One?

Single-responsibility MCP servers are:
- Independently testable and deployable
- Replaceable (swap market data provider without touching portfolio logic)
- Auditable (each server has a clear scope of what data it accesses)
- Scalable (high-traffic servers can be scaled independently)

### Why Streamlit Over Flask/FastAPI + React?

For a financial AI application in early stages:
- Streamlit allows rapid iteration on data visualization
- Built-in session state simplifies multi-step agent interactions
- Plotly/Altair integration is native
- The user can validate UX before committing to a production frontend

The `fluid_requirements.yaml` includes a migration path to a React frontend if Streamlit proves limiting.

### Why SQLite First?

The portfolio database starts with SQLite because:
- Zero operational overhead for development
- Full SQL capability for complex portfolio queries
- Easy to inspect and debug
- SQLAlchemy abstraction layer means PostgreSQL migration is a schema + connection string change

### Agent Orchestration Pattern

The Orchestrator Agent uses a **router pattern** rather than a **pipeline pattern**. User queries are classified by intent, then routed to the most appropriate specialist agent. Multiple agents can be invoked in sequence for complex queries (e.g., "Should I sell AAPL?" → Market Researcher → Risk Analyst → Portfolio Advisor → Trade Reviewer).

### Financial Data Reliability Strategy

Market data APIs have reliability issues (rate limits, stale data, outages). The architecture includes:
- **Cache layer** in `market-data-mcp` (5-minute TTL for prices, 24-hour for fundamentals)
- **Fallback providers** (Alpha Vantage → Yahoo Finance fallback)
- **Staleness indicators** in the UI when data is cached

### The "No Financial Advice" Guardrail

This is the most critical guardrail. All AI-generated recommendations must:
1. Be framed as "analysis" or "considerations" not "advice"
2. Include mandatory disclaimers in every response
3. Never reference specific buy/sell price targets as instructions
4. Always recommend consulting a licensed financial advisor for material decisions

This is encoded in `guardrails.yaml` and referenced in every agent's system prompt.
