# FinApp — Architecture & High-Level Design Diagrams

---

## 1. System Architecture Diagram

```mermaid
graph TB
    subgraph User["User Interface Layer"]
        UI[Streamlit GUI]
        AUTH[Auth Module]
    end

    subgraph Orchestration["Agent Orchestration Layer"]
        ORCH[Orchestrator Agent]
        PA[Portfolio Advisor Agent]
        RA[Risk Analyst Agent]
        MR[Market Researcher Agent]
        NS[News Sentinel Agent]
        FP[Financial Planner Agent]
        TR[Trade Reviewer Agent]
    end

    subgraph MCP["MCP Server Layer"]
        MDP[market-data-mcp]
        NMP[news-mcp]
        PMP[portfolio-mcp]
        CMP[calculator-mcp]
        SMP[search-mcp]
        EMP[export-mcp]
    end

    subgraph External["External Data Sources"]
        YF[Yahoo Finance API]
        AV[Alpha Vantage API]
        NA[NewsAPI]
        EDGAR[SEC EDGAR]
        BSEARCH[Brave Search]
    end

    subgraph Data["Data Layer"]
        DB[(SQLite / PostgreSQL)]
        CACHE[(Redis Cache)]
        FILES[File Storage]
    end

    subgraph AI["AI Services"]
        CLAUDE[Claude API\nclaude-sonnet-4-6]
    end

    %% User to Orchestration
    UI --> ORCH
    AUTH --> UI

    %% Orchestrator routes to agents
    ORCH --> PA
    ORCH --> RA
    ORCH --> MR
    ORCH --> NS
    ORCH --> FP
    ORCH --> TR

    %% Agents use Claude
    PA --> CLAUDE
    RA --> CLAUDE
    MR --> CLAUDE
    NS --> CLAUDE
    FP --> CLAUDE
    TR --> CLAUDE
    ORCH --> CLAUDE

    %% Agents use MCP tools
    PA --> PMP
    PA --> MDP
    RA --> CMP
    RA --> PMP
    MR --> MDP
    MR --> SMP
    NS --> NMP
    FP --> PMP
    FP --> CMP
    TR --> PMP
    TR --> MDP

    %% MCP servers to external APIs
    MDP --> YF
    MDP --> AV
    MDP --> CACHE
    NMP --> NA
    NMP --> EDGAR
    SMP --> BSEARCH
    EMP --> FILES

    %% MCP servers to database
    PMP --> DB
    CMP --> DB

    style User fill:#1e3a5f,color:#fff
    style Orchestration fill:#1a4d2e,color:#fff
    style MCP fill:#4a1a5f,color:#fff
    style External fill:#5f3a1a,color:#fff
    style Data fill:#3a3a1a,color:#fff
    style AI fill:#1a3a5f,color:#fff
```

---

## 2. High-Level Design Diagram — Component Interactions

```mermaid
sequenceDiagram
    actor User
    participant GUI as Streamlit GUI
    participant Orch as Orchestrator Agent
    participant Spec as Specialist Agent
    participant MCP as MCP Server
    participant Ext as External API
    participant DB as Database
    participant Claude as Claude API

    User->>GUI: Submit query or action
    GUI->>Orch: Forward with session context
    Orch->>Claude: Classify intent & determine routing
    Claude-->>Orch: Route to: [SpecialistAgent]
    Orch->>Spec: Dispatch with context
    Spec->>Claude: Reason with tools
    Claude-->>Spec: Tool call: mcp_tool(params)
    Spec->>MCP: Execute tool call
    MCP->>Ext: Fetch from external API (if needed)
    Ext-->>MCP: Raw data response
    MCP->>DB: Cache/persist data
    MCP-->>Spec: Structured tool result
    Spec->>Claude: Continue reasoning with result
    Claude-->>Spec: Final analysis + recommendation
    Spec-->>Orch: Agent response
    Orch-->>GUI: Formatted response + metadata
    GUI-->>User: Display result with charts/tables
```

---

## 3. Data Flow Diagram — Portfolio Analysis

```mermaid
flowchart LR
    subgraph Input
        A[User Portfolio\nHoldings CSV]
        B[Manual Entry\nvia GUI]
        C[Market Data\nReal-time Feed]
    end

    subgraph Processing
        D[Portfolio Ingestion\nPortfolio MCP]
        E[Valuation Engine\nCalculator MCP]
        F[Risk Calculator\nCalculator MCP]
        G[Performance\nAttribution]
    end

    subgraph AI_Analysis
        H[Portfolio Advisor\nAgent]
        I[Risk Analyst\nAgent]
        J[News Sentinel\nAgent]
    end

    subgraph Output
        K[Dashboard\nStreamlit]
        L[Risk Report\nPDF Export]
        M[Recommendations\nChat Interface]
        N[Alerts\nNotifications]
    end

    A --> D
    B --> D
    C --> E
    D --> E
    E --> F
    E --> G
    F --> I
    G --> H
    D --> J
    H --> M
    I --> L
    I --> N
    J --> K
    G --> K
    H --> K
    L --> Output
    M --> Output
```

---

## 4. Agent Orchestration Flow

```mermaid
stateDiagram-v2
    [*] --> UserQuery
    UserQuery --> IntentClassification: Submit query
    IntentClassification --> PortfolioAdvisor: "investment advice / recommendations"
    IntentClassification --> RiskAnalyst: "risk / exposure / VaR / stress test"
    IntentClassification --> MarketResearcher: "research / analyse security / sector"
    IntentClassification --> NewsSentinel: "news / sentiment / what happened"
    IntentClassification --> FinancialPlanner: "budget / plan / goals / savings"
    IntentClassification --> TradeReviewer: "buy / sell / trade review"
    IntentClassification --> MultiAgent: "complex query requiring multiple agents"

    PortfolioAdvisor --> ResponseAggregation
    RiskAnalyst --> ResponseAggregation
    MarketResearcher --> ResponseAggregation
    NewsSentinel --> ResponseAggregation
    FinancialPlanner --> ResponseAggregation
    TradeReviewer --> ResponseAggregation

    MultiAgent --> PortfolioAdvisor
    MultiAgent --> RiskAnalyst
    MultiAgent --> MarketResearcher

    ResponseAggregation --> GuardrailCheck: Apply compliance rules
    GuardrailCheck --> DisclaimerInjection: Add required disclaimers
    DisclaimerInjection --> StreamlitDisplay
    StreamlitDisplay --> [*]
```

---

## 5. MCP Server Architecture

```mermaid
graph TB
    subgraph AgentLayer["Agent Layer (Clients)"]
        A1[Portfolio Advisor]
        A2[Risk Analyst]
        A3[Market Researcher]
        A4[News Sentinel]
        A5[Financial Planner]
    end

    subgraph MCPLayer["MCP Protocol Layer"]
        direction TB

        subgraph MDMCP["market-data-mcp"]
            MD1[get_quote]
            MD2[get_historical_prices]
            MD3[get_fundamentals]
            MD4[get_technical_indicators]
        end

        subgraph NMCP["news-mcp"]
            N1[search_news]
            N2[get_sentiment_score]
            N3[get_sec_filings]
            N4[summarize_article]
        end

        subgraph PMCP["portfolio-mcp"]
            P1[get_portfolio]
            P2[add_holding]
            P3[update_holding]
            P4[get_performance]
            P5[get_transactions]
        end

        subgraph CMCP["calculator-mcp"]
            C1[calculate_var]
            C2[calculate_sharpe]
            C3[run_stress_test]
            C4[calculate_irr]
            C5[optimize_weights]
        end
    end

    subgraph DataLayer["Data & External"]
        EXT1[Yahoo Finance]
        EXT2[Alpha Vantage]
        EXT3[NewsAPI]
        DB[(Database)]
        CACHE[(Cache)]
    end

    A1 --> PMCP
    A1 --> MDMCP
    A2 --> CMCP
    A2 --> PMCP
    A3 --> MDMCP
    A4 --> NMCP
    A5 --> PMCP
    A5 --> CMCP

    MDMCP --> EXT1
    MDMCP --> EXT2
    MDMCP --> CACHE
    NMCP --> EXT3
    PMCP --> DB
    CMCP --> DB
```

---

## 6. Streamlit GUI Layout

```mermaid
graph TD
    subgraph App["FinApp — Streamlit Application"]
        NAV[Sidebar Navigation]

        subgraph Pages["Pages"]
            P1[📊 Dashboard\nPortfolio overview, KPIs, charts]
            P2[💼 Portfolio\nHoldings, add/edit, transactions]
            P3[🤖 AI Advisor\nChat interface with agents]
            P4[📈 Market\nQuotes, research, watchlist]
            P5[⚠️ Risk\nVaR, stress tests, alerts]
            P6[📰 News\nFeed, sentiment, company news]
            P7[💰 Planning\nBudget, goals, projections]
            P8[📑 Reports\nGenerate and export reports]
            P9[⚙️ Settings\nAPI keys, preferences, profile]
        end
    end

    NAV --> P1
    NAV --> P2
    NAV --> P3
    NAV --> P4
    NAV --> P5
    NAV --> P6
    NAV --> P7
    NAV --> P8
    NAV --> P9
```
