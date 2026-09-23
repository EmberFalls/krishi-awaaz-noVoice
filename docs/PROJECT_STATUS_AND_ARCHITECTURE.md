# Krishi Awaaz: Project Status, Architecture, and Technology Roadmap

**Document status:** prototype handoff and technical baseline  
**Current version:** `0.1.0`  
**Last verified state:** local text simulation, local voice simulation, and live-ready webhook code  
**Audience:** project team, reviewers, and future contributors

## 1. What Krishi Awaaz Is

Krishi Awaaz is a **multilingual, voice-first agricultural market-assistance system**. A farmer should be able to describe a crop lot in a preferred language, state sale constraints, receive market-aware buyer options, and receive a clear, non-binding recommendation.

The current repository is a **working prototype**, not a production marketplace. It demonstrates the complete logical path from farmer intake to negotiation and recommendation using fictional scenarios and deterministic rules. It also contains the boundaries required for a future real phone-call implementation.

### Core problem addressed

Small farmers can face information asymmetry: limited visibility of buyer demand, unclear price comparisons, transport costs, delayed payment risk, and limited ability to contact several buyers quickly. Krishi Awaaz is designed to make those trade-offs visible before a farmer accepts a quote.

### Current product promise

The prototype can:

- collect or replay sale details in multiple Indian languages;
- compare synthetic local-market net returns;
- identify buyers that satisfy crop, quantity, capacity, quality, pickup, and availability constraints;
- negotiate with qualifying simulated buyers concurrently;
- rank provisional offers by **risk-adjusted net return**, not headline price alone; and
- produce a farmer-facing recommendation that explicitly requires human confirmation and physical inspection.

The prototype does **not** place orders, transfer money, create a binding sale, contact a real buyer, or use real market prices.

---

## 2. Scope Completed So Far

### 2.1 Scenario and language layer

Implemented fictional test data in `data/scenarios.json`:

- 4 farmer scenarios:
  - Marathi farmer in Nashik selling onions;
  - Punjabi farmer in Ludhiana selling wheat;
  - Tamil farmer in Madurai selling tomatoes;
  - Telugu farmer in Guntur selling dried chillies.
- 3 simulated middlemen per scenario, for **12 middlemen total**.
- Each scenario includes farmer profile, location, produce listing, synthetic market snapshots, buyer constraints, and scripted dialogue.
- Every scripted non-English dialogue line includes an English translation for review.
- The deterministic free-form intake extractor additionally recognizes English, Hindi, Marathi, Punjabi, Tamil, Telugu, and mixed-language crop/quantity/price phrases.

### 2.2 Farmer intake layer

Implemented two compatible intake modes:

1. **Scripted local intake** for stable demonstrations and regression tests.
2. **Free-form transcript intake** for the live-call path.

The free-form rule-based extractor collects these fields when they are explicitly present:

- crop and local crop name;
- quantity in quintals;
- minimum acceptable price per quintal;
- village;
- buyer pickup versus farmer delivery preference; and
- same-day or bank-transfer payment preference.

When required details are missing, the system asks a focused follow-up. Low-confidence transcription results trigger a retry, and the system ends a failed intake after a bounded retry limit.

### 2.3 Market and negotiation layer

Implemented plain-Python workflow nodes:

- `intake_node`: transforms a validated listing into a typed `FarmerRequest`;
- `market_decision_node`: compares synthetic markets after transport and fees;
- `buyer_selection_node`: filters buyers using crop, quantity, availability, capacity, and quality constraints;
- `parallel_negotiation_node`: negotiates with eligible buyers concurrently;
- `ranking_node`: ranks qualified offers; and
- `reporting_node`: creates the final non-binding farmer report.

Each simulated buyer can include:

- supported crops;
- minimum and maximum lot size;
- available purchasing capacity;
- accepted quality keywords;
- opening offer, private maximum offer, and per-round concession;
- pickup availability and farmer transport cost;
- handling cost and payment delay;
- reliability score; and
- competing-demand price modifier.

The negotiation records price, quantity, pickup, payment, quality-related conditions, rounds, and a provisional status. A buyer's maximum price is hidden simulator state and is never treated as external market evidence by the negotiation workflow.

### 2.4 Voice and telephony layer

Implemented provider-neutral voice contracts plus two implementations:

- **Local simulation:** deterministic scripted speech-to-text and capturing text-to-speech adapters. No phone, microphone, API key, network, or database is required.
- **Live-ready webhook path:** Twilio webhook handlers, Twilio signature validation, recording download, Sarvam speech-to-text, Sarvam text-to-speech, and TwiML responses.

The live path is code-complete enough to test with a Twilio number once credentials and a public HTTPS URL are configured. No real provider request, phone call, or credential has been used by the project yet.

### 2.5 Persistence layer

Implemented PostgreSQL persistence for:

- farmers and locations;
- produce listings;
- synthetic market snapshots;
- middlemen and constraints;
- simulation runs and workflow events;
- intake and negotiation messages;
- offers and rankings;
- voice-call sessions and extracted intake drafts;
- voice-call transcripts; and
- generated prompt audio for development-scale persistence.

The system rejects SQLite URLs deliberately. PostgreSQL is the only supported persistence target.

### 2.6 Developer tooling and verification

Implemented:

- command-line interface for listing, inspecting, running, initializing, and reviewing calls;
- Docker Compose configuration for local PostgreSQL;
- PowerShell test runner;
- unit, workflow, webhook, telephony, extraction, buyer-constraint, schema, and opt-in PostgreSQL integration tests;
- Ruff linting and formatting checks; and
- Python compilation checks.

Latest local verification:

```text
17 tests passed
1 PostgreSQL integration test skipped unless Docker is available and requested
Ruff lint: passed
Ruff formatting check: passed
Python compilation check: passed
Local voice-demo: completed successfully
```

---

## 3. Exact Current Architecture

The diagram is deliberately vertical so it can be copied into one Google Slide without becoming too wide.

```text
                         ┌───────────────────────────────┐
                         │          FARMER INPUT          │
                         │ Scripted text / voice transcript│
                         └───────────────┬───────────────┘
                                         │
                                         ▼
                  ┌────────────────────────────────────────────┐
                  │          INTAKE AND LANGUAGE LAYER          │
                  │ - scripted demo adapter OR Sarvam STT       │
                  │ - multilingual rule extraction              │
                  │ - missing-field follow-up questions         │
                  │ - typed FarmerRequest                       │
                  └───────────────────┬────────────────────────┘
                                      │
                                      ▼
                  ┌────────────────────────────────────────────┐
                  │          MARKET DECISION LAYER              │
                  │ Synthetic mandi snapshots                   │
                  │ modal price - transport - fees               │
                  │ → ranked estimated net return               │
                  └───────────────────┬────────────────────────┘
                                      │
                                      ▼
                  ┌────────────────────────────────────────────┐
                  │          BUYER SELECTION LAYER              │
                  │ Crop | quantity | capacity | quality         │
                  │ availability | pickup constraints            │
                  └───────────────────┬────────────────────────┘
                                      │
                                      ▼
                  ┌────────────────────────────────────────────┐
                  │     PARALLEL NEGOTIATION AGENTS             │
                  │ asyncio.gather runs each eligible buyer      │
                  │ Price | pickup | costs | payment | reliability│
                  └───────────────────┬────────────────────────┘
                                      │
                                      ▼
                  ┌────────────────────────────────────────────┐
                  │       OFFER RANKING AND REPORTING           │
                  │ Risk-adjusted net return                    │
                  │ → non-binding farmer recommendation         │
                  └───────────────────┬────────────────────────┘
                                      │
                                      ▼
                  ┌────────────────────────────────────────────┐
                  │           PERSISTENCE / REVIEW              │
                  │ PostgreSQL runs, offers, transcripts, calls │
                  │ CLI output now; dashboard later             │
                  └────────────────────────────────────────────┘

Optional live voice boundary:

Twilio number → POST /twilio/voice → FastAPI → TwiML <Play>/<Record>
                                        │
                                        ▼
                            Sarvam STT / Sarvam TTS
                                        │
                                        ▼
                            Same intake → workflow above
```

### Architecture principles

- **Plain Python orchestration:** no LangGraph, LangChain, CrewAI, AutoGen, or other agent framework is used.
- **Deterministic first:** price logic, offer ranking, and current text extraction are reproducible and testable.
- **Provider boundary:** telephony and speech providers are isolated behind Python contracts.
- **Typed data:** Pydantic models carry data between layers instead of unstructured prompt text.
- **No binding commerce:** all outputs remain provisional recommendations.

---

## 4. Exact Technology Stack Used Today

### 4.1 Runtime and application code

| Area | Technology | Current role |
|---|---|---|
| Language | Python 3.11+ | Entire backend, workflow, CLI, tests |
| Packaging | Hatchling / `pyproject.toml` | Package build and command registration |
| Data validation | Pydantic `>=2.10,<3.0` | Typed domain, voice, and result models |
| Orchestration | Plain Python + `asyncio.gather` | Ordered workflow and concurrent simulated negotiations |
| Domain extraction | Python regular expressions + Pydantic | Deterministic multilingual intake fields |
| Scenario storage | JSON | Fictional fixtures in `data/scenarios.json` |
| CLI UI | Rich | Tables, panels, transcript and result output |

### 4.2 Database and local infrastructure

| Area | Technology | Current role |
|---|---|---|
| Database | PostgreSQL | Only supported persistence database |
| ORM | SQLAlchemy `>=2.0,<3.0` | Schema and database reads/writes |
| PostgreSQL driver | psycopg 3 | Python database connection |
| Local database runtime | Docker Compose + PostgreSQL 18 Alpine | Optional local PostgreSQL container |
| Schema management today | SQLAlchemy metadata `create_all` | Initial prototype schema creation |

### 4.3 Voice stack

| Area | Technology | Current role |
|---|---|---|
| HTTP application | FastAPI | Incoming voice webhook routes and health endpoint |
| ASGI server | Uvicorn | Runs the optional live server |
| Telephony | Twilio Python SDK | TwiML and webhook signature validation |
| Speech-to-text | Sarvam AI Python SDK | Sarvam `saaras:v3` adapter in live code |
| Text-to-speech | Sarvam AI Python SDK | Sarvam `bulbul:v3` adapter in live code |
| HTTP downloads | HTTPX | Downloads Twilio recordings for transcription |
| Multipart parsing | python-multipart | Parses Twilio webhook forms |
| Live development storage | PostgreSQL audio rows or in-memory audio store | Serves generated prompt audio |

### 4.4 Quality tooling

| Area | Technology | Current role |
|---|---|---|
| Test framework | pytest | Unit, workflow, webhook, and integration tests |
| Linting and formatting | Ruff | Static checks and formatting validation |
| Test automation | PowerShell `scripts/run_tests.ps1` | Standard checks, optional Docker-backed PostgreSQL test |

### 4.5 Explicitly not used today

- No LangGraph, LangChain, CrewAI, AutoGen, or other agent framework.
- No LLM API in the currently implemented workflow.
- No OpenAI API, Gemini API, Anthropic API, or local language model.
- No real Agmarknet/data.gov.in, weather, payments, logistics, or buyer APIs.
- No React, Android, Flutter, web frontend, or dashboard application.
- No Redis, Celery, Kafka, background job queue, vector database, or object storage.
- No real Twilio phone number, tunnel, Sarvam key, or deployed cloud service configured by the project.

---

## 5. Repository Map

```text
krishi-awaaz/
├── agents/
│   ├── intake.py              # Multilingual rule extraction and follow-up prompts
│   ├── localization.py        # Bilingual negotiation templates
│   ├── models.py              # Pydantic domain models
│   └── negotiation.py         # Market assessment, negotiation, ranking
├── data/
│   ├── scenarios.json         # Fictional multilingual scenarios
│   └── scenarios.py           # Scenario loading and lookup
├── db/
│   └── database.py            # SQLAlchemy PostgreSQL schema and store
├── orchestration/
│   ├── workflow.py            # Plain-Python workflow nodes
│   ├── cli.py                 # Terminal commands and output
│   └── config.py              # Database and scenario settings
├── telephony/
│   ├── contracts.py           # Provider-neutral voice contracts
│   ├── simulated.py           # Local deterministic speech adapters
│   ├── service.py             # Scripted local voice demo
│   ├── live.py                # Live free-form call coordinator
│   ├── sarvam.py              # Sarvam STT/TTS adapters
│   ├── webhook_routes.py      # Twilio/FastAPI webhook app
│   ├── settings.py            # Voice environment configuration
│   └── server.py              # Uvicorn entry point
├── tests/                     # 18 test cases, including PostgreSQL integration coverage
├── scripts/run_tests.ps1      # Standard test automation
├── compose.yaml               # Local PostgreSQL service
├── .env.example               # Example environment variable names only
├── pyproject.toml             # Dependencies and packaging
└── README.md                  # Setup and operating guide
```

`dashboard/`, `agents/prompts/`, and several documentation folders are reserved for future work; they are not functioning product components yet.

---

## 6. Current Commands

All commands are run from the repository root after activating the virtual environment.

```powershell
# Install core development dependencies
python -m pip install -e ".[dev]"

# Install live voice dependencies as well
python -m pip install -e ".[dev,voice]"

# List test scenarios
python -m orchestration.cli list

# Inspect a scenario and simulator-only buyer ceilings
python -m orchestration.cli show nashik-onion-001

# Run one simulation without PostgreSQL
python -m orchestration.cli run nashik-onion-001 --no-db

# Replay the deterministic local voice demo
python -m orchestration.cli voice-demo nashik-onion-001

# Start local PostgreSQL when Docker Desktop is available
docker compose up -d postgres

# Create schema and seed fixtures
python -m orchestration.cli db-init

# Run a persisted simulation
python -m orchestration.cli run nashik-onion-001

# Show persisted voice-call sessions
python -m orchestration.cli calls

# Run standard automated checks
.\scripts\run_tests.ps1

# Run checks including Docker-backed PostgreSQL integration test
.\scripts\run_tests.ps1 -WithPostgres
```

The live server requires real credentials and a public HTTPS URL:

```powershell
$env:TWILIO_ACCOUNT_SID = "..."
$env:TWILIO_AUTH_TOKEN = "..."
$env:SARVAM_API_KEY = "..."
$env:VOICE_PUBLIC_BASE_URL = "https://your-public-address.example"
$env:VOICE_SCENARIO_ID = "nashik-onion-001"
$env:DATABASE_URL = "postgresql+psycopg://krishi:krishi@localhost:5432/krishi_awaaz"
python -m telephony.server
```

The current code reads environment variables directly. Copying `.env.example` to `.env` is useful as a private checklist, but it does **not** load variables automatically.

---

## 7. Data, Safety, and Product Boundaries

### Current data boundaries

- All people, phone aliases, prices, buyer terms, and market information in the repository are fictional.
- Synthetic market data must not be presented as a real mandi quote.
- Simulated buyer responses must not be presented as real commercial offers.
- Voice-call recording data has not been collected or tested with real people.

### Commercial and safety boundaries

- A recommendation is not a contract, order, invoice, payment instruction, or sale confirmation.
- Physical quality and weight inspection are still required before any real transaction.
- Real farmers must hear a consent notice before recording begins.
- Real transcripts/audio need a retention period, access control, deletion process, and encrypted storage plan.
- The current database audio persistence is suitable only for development-scale testing. Production should use encrypted object storage and a deliberate retention policy.

---

## 8. Next Technology Stack and Implementation Order

The current stack should mostly remain. Add components only when the corresponding product stage is reached.

### Stage A: Real controlled phone testing

**Add/configure:**

- Twilio account and voice-enabled number;
- Sarvam API key;
- ngrok or another public HTTPS tunnel for development;
- Docker Desktop for local PostgreSQL verification; and
- a short caller consent message plus a test-call checklist.

**Outcome:** team members can make controlled calls from approved numbers and inspect transcripts, extracted details, offers, and reports.

### Stage B: Better conversational understanding

**Potential additions:**

- an LLM provider with structured JSON output, selected by the team;
- Pydantic schema validation after every model response;
- a curated multilingual evaluation set of consented/transcribed farmer utterances;
- confidence thresholds and mandatory human confirmation for uncertain details.

**Recommendation:** keep deterministic extraction as a fallback even if an LLM is added. Do not let an LLM directly make a binding price or sale decision.

### Stage C: Live market and operational data

**Potential additions:**

- Agmarknet or data.gov.in mandi-price integration;
- weather provider such as Open-Meteo or WeatherAPI;
- cached price snapshots in PostgreSQL;
- data timestamping, source attribution, and freshness validation.

**Outcome:** the current synthetic market decision node can consume real, dated data.

### Stage D: Real buyer workflow

**Potential additions:**

- verified buyer onboarding and authorization;
- buyer availability/capacity interface;
- human-approved offer messaging;
- payment and logistics integrations only after legal and operational review;
- audit trail, dispute handling, and buyer/farmer confirmation steps.

**Outcome:** replace simulated middlemen incrementally; do not automate binding negotiation before clear approvals exist.

### Stage E: Dashboard and deployment

**Recommended additions:**

| Need | Recommended technology |
|---|---|
| Database migrations | Alembic |
| Internal dashboard | React + TypeScript + Vite, or a smaller FastAPI/Jinja dashboard first |
| Background tasks | FastAPI background tasks initially; Celery + Redis only when workload requires it |
| Production audio storage | Encrypted S3-compatible object storage |
| Monitoring | Structured logging, Sentry, health checks, and alerting |
| Deployment | Docker Compose initially; later a managed cloud platform selected by the team |
| Authentication | Role-based authentication for staff, buyers, and administrators |

---

## 9. Completion Estimate

This is a **scope-based estimate**, not a time estimate.

```text
Overall Krishi Awaaz vision

Completed prototype foundation:  █████████░░░░░░░░░░░  45%
Remaining product work:          ███████████░░░░░░░░░  55%
```

### What makes up the completed 45%

- 100% of the fictional, deterministic text-simulation prototype;
- 100% of the plain-Python multi-buyer workflow prototype;
- 100% of the initial multilingual fixture layer;
- 100% of the local simulated voice demo;
- 80% of a development-ready telephony integration boundary;
- 75% of the initial PostgreSQL schema and persistence layer; and
- 70% of prototype-level automated test coverage.

### What makes up the remaining 55%

- real credential and phone-number setup;
- real-call testing and multilingual evaluation;
- production-grade free-form understanding and confirmation;
- live market, weather, buyer, logistics, and payment integrations;
- dashboard and user-facing applications;
- deployment, operations, monitoring, migrations, and security hardening;
- consent, privacy, data retention, and commercial processes; and
- real buyer onboarding and controlled production rollout.

The percentage should not be interpreted as “nearly ready to launch.” The hardest and highest-risk parts—real people, real money, real data, privacy, and operational reliability—remain in the final 55%.

---

## 10. Final Status Summary

Krishi Awaaz currently has a complete and testable **simulation core**: multilingual farmer details enter a typed workflow, synthetic markets are compared, eligible simulated buyers negotiate concurrently, offers are ranked, and a clear provisional recommendation is produced. The code deliberately avoids unnecessary orchestration frameworks and uses ordinary Python, typed models, deterministic rules, PostgreSQL, and provider-neutral voice boundaries.

The next milestone is not more simulation. It is a **small, controlled real-call test** using one Twilio number, Sarvam credentials, PostgreSQL, a public HTTPS tunnel, team test callers, consent language, and careful transcript review. After that, the team can decide whether an LLM, live market data, real buyers, and a dashboard are justified.

---

## 11. Backend Technology Architecture

This is the **technology integration view**, rather than the farmer-facing product flow. Solid paths are implemented in the codebase; dashed paths require real credentials and a public deployment before they operate.

```text
                    ┌───────────────────────────────────────┐
                    │          Python application            │
                    │       (one shared codebase)            │
                    └───────────────────┬───────────────────┘
                                        │
          ┌─────────────────────────────┼─────────────────────────────┐
          │                             │                             │
          v                             v                             v
┌─────────────────────┐    ┌─────────────────────────┐    ┌─────────────────────┐
│ CLI / local runner  │    │ FastAPI web application │    │ Pytest test runner  │
│ orchestration.cli   │    │ telephony.webhook_routes│    │ unit + integration  │
└─────────┬───────────┘    └───────────┬─────────────┘    └─────────────────────┘
          │                            │
          │                            │  - - real-call HTTP webhooks - -
          │                            v
          │              ┌───────────────────────────────┐
          │              │ Twilio Voice platform          │
          │              │ phone number, call control,    │
          │              │ recordings, webhook requests   │
          │              └───────────────┬───────────────┘
          │                              │
          │                 - - audio/API requests - -
          │                              v
          │              ┌───────────────────────────────┐
          │              │ Sarvam AI APIs                 │
          │              │ STT: Saaras v3                 │
          │              │ TTS: Bulbul v3                 │
          │              └───────────────┬───────────────┘
          │                              │
          └───────────────┬──────────────┘
                          v
          ┌───────────────────────────────────────────┐
          │ Application service layer                  │
          │ telephony.live / telephony.service         │
          │ • call state and retry handling            │
          │ • transcript-to-field extraction           │
          │ • provider-neutral STT/TTS contracts       │
          └─────────────────────┬─────────────────────┘
                                v
          ┌───────────────────────────────────────────┐
          │ Plain-Python decision layer                │
          │ agents.intake + agents.negotiation         │
          │ orchestration.workflow                     │
          │ • Pydantic typed data                      │
          │ • deterministic rules                      │
          │ • asyncio.gather for parallel buyers       │
          └─────────────────────┬─────────────────────┘
                                v
          ┌───────────────────────────────────────────┐
          │ SQLAlchemy persistence layer               │
          │ db.database / PostgresStore                │
          │ object-to-SQL mapping and DB transactions  │
          └─────────────────────┬─────────────────────┘
                                v
          ┌───────────────────────────────────────────┐
          │ PostgreSQL + psycopg                       │
          │ farmers, listings, markets, offers, runs,  │
          │ call history, messages, generated audio    │
          └───────────────────────────────────────────┘

Local development infrastructure:
Docker Compose ──> PostgreSQL container
```

### How the backend technologies divide responsibility

| Technology | Responsibility in the backend | Current state |
|---|---|---|
| Python 3.11+ | Main language; hosts every local module and the CLI | Implemented |
| Pydantic | Validates and structures data crossing module boundaries | Implemented |
| `asyncio` | Runs independent simulated buyer negotiations concurrently | Implemented |
| FastAPI + Uvicorn | Exposes health and Twilio webhook HTTP endpoints | Implemented; needs deployment for live traffic |
| Twilio SDK/platform | Validates webhook signatures, controls calls, accepts recordings | Adapter implemented; credentials/number still needed |
| Sarvam SDK/API | Speech-to-text and text-to-speech for live calls | Adapter implemented; API key and live evaluation still needed |
| SQLAlchemy | Database schema, query construction, transactions | Implemented |
| psycopg | PostgreSQL driver used by SQLAlchemy | Implemented |
| PostgreSQL | Durable relational store for simulation and call records | Schema implemented; live local instance needs Docker/manual setup |
| Docker Compose | Starts PostgreSQL consistently on a developer machine | Implemented |
| pytest | Runs automated behavior and persistence tests | Implemented |

### Important backend design choices

- The HTTP/voice adapters do not contain market logic. They collect audio and hand normalized information to the same Python workflow the CLI uses.
- The decision workflow has no runtime dependency on Twilio, Sarvam, FastAPI, or an LLM. This keeps the simulator testable without network access or paid credentials.
- Provider-specific code is confined to `telephony/sarvam.py` and Twilio-facing webhook code, so another speech provider can later replace Sarvam without rewriting negotiation logic.
- Database writes happen through `PostgresStore`; agents do not run raw SQL themselves.
- The present workflow uses deterministic code, not LangGraph, LangChain, CrewAI, AutoGen, or an LLM API. An LLM can be added behind a narrow extraction/advice interface only after baseline evaluation proves it is needed.
