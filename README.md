# Krishi Awaaz simulation

This repository contains the text-first simulation layer for Krishi Awaaz plus a local,
provider-neutral voice-call foundation. The optional live server is ready to use Twilio and
Sarvam after the team supplies credentials; it does not make real phone calls by itself. The
purpose of this stage is to make farmer intake, market comparison, middleman negotiation,
ranking, and reporting behavior visible and repeatable before real speech recognition makes the
inputs less predictable.

All names, phone aliases, market prices, and commercial terms in `data/scenarios.json` are
fictional test data. They must not be treated as current market information or real offers.

## Current architecture

```text
Free-form multilingual farmer turn
    -> Rule-based intake extraction + targeted follow-up questions
    -> Typed FarmerRequest
    -> Decision node (synthetic market net-return comparison)
    -> Buyer-selection node (crop and quantity constraints)
    -> Parallel deterministic negotiation nodes
    -> Offer ranker (risk-adjusted net return)
    -> Non-binding farmer report
```

Plain Python defines the node order and shared state, while `asyncio.gather` runs independent
middleman negotiations concurrently. All domain models, price rules, negotiation rules, and
PostgreSQL persistence remain ordinary Python modules.

The catalog currently covers four farmers speaking Marathi, Punjabi, Tamil, and Telugu, with
three middlemen per farmer. The voice extractor also recognizes Hindi, English, and mixed-language
crop/quantity/price phrases. Every non-English scripted conversation line includes an English
translation for review.

## Project structure

```text
krishi-awaaz/
├── telephony/           # Voice contracts and deterministic local call simulation
├── agents/              # Domain models, negotiation logic, language templates
│   └── prompts/         # Reserved for future model prompts
├── orchestration/       # Plain-Python workflow, configuration, CLI
├── data/                # Scenario loader and synthetic multilingual fixtures
├── db/                  # PostgreSQL schema and persistence
├── dashboard/           # Reserved for the future internal dashboard
├── tests/               # Unit and workflow tests
├── scripts/             # Reserved for setup and utility scripts
├── docs/                # Reserved for internal documentation
└── krishi_awaaz/        # Compatibility launcher for `python -m krishi_awaaz`
```

Only the components already implemented contain application code. The dashboard, prompts,
scripts, and docs folders are placeholders for later project stages.

## Set up Python

Python 3.11 or newer is required.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

List and inspect the fixtures:

```powershell
python -m orchestration.cli list
python -m orchestration.cli show nashik-onion-001
```

Run a complete simulation without requiring PostgreSQL:

```powershell
python -m orchestration.cli run nashik-onion-001 --no-db
```

Use `--json` when you want the typed output rather than the review-oriented transcript.

## Local voice-call demo

The `voice-demo` command replays a scripted farmer intake through local, deterministic
speech-to-text and text-to-speech substitutes, then invokes the unchanged negotiation workflow.
It does not use a phone number, microphone, audio file, database, network connection, or API key.

```powershell
python -m orchestration.cli voice-demo nashik-onion-001
```

This is the first voice milestone. A later provider adapter will implement the same contracts for
real call audio, while the existing workflow remains unchanged.

## Live inbound-call server

The optional live server receives Twilio voice webhooks, records short caller turns, transcribes
them with Sarvam, and plays Sarvam-generated audio prompts. It validates Twilio request signatures
by default. It extracts crop, quantity, minimum price, village, and pickup preference using local
deterministic rules and asks a focused question for each missing required field. The selected
scenario remains the source of synthetic market and buyer fixtures for the prototype.

Install the optional voice dependencies:

```powershell
python -m pip install -e ".[dev,voice]"
```

Set the values in `.env.example` as PowerShell environment variables. `VOICE_PUBLIC_BASE_URL` must
be the HTTPS address publicly reachable by Twilio, for example an HTTPS tunnel during development.

```powershell
$env:TWILIO_ACCOUNT_SID = "..."
$env:TWILIO_AUTH_TOKEN = "..."
$env:SARVAM_API_KEY = "..."
$env:VOICE_PUBLIC_BASE_URL = "https://your-public-address.example"
python -m telephony.server
```

Configure the voice-enabled Twilio number to send a `POST` request to:

```text
https://your-public-address.example/twilio/voice
```

When `DATABASE_URL` is set for the live server, call sessions, transcripts, results, and generated
prompt audio are retained in PostgreSQL. This is suitable for local development and review. A
production deployment still needs encrypted object storage with a retention policy for audio,
HTTPS, consent language, and real-call review before accepting farmer traffic.

## PostgreSQL

The application only accepts a PostgreSQL SQLAlchemy URL for persistence. It does not silently
fall back to SQLite.

If Docker is available:

```powershell
docker compose up -d postgres
Copy-Item .env.example .env
$env:DATABASE_URL = "postgresql+psycopg://krishi:krishi@localhost:5432/krishi_awaaz"
python -m orchestration.cli db-init
python -m orchestration.cli run nashik-onion-001
```

The schema stores:

- simulated farmer profiles and locations;
- produce listings and minimum-price constraints;
- synthetic market snapshots and logistics estimates;
- simulated middleman profiles and hidden test constraints;
- simulation runs and workflow events;
- every original-language message and its English translation;
- provisional offers, costs, rankings, and risk-adjusted totals.

`db-init` uses SQLAlchemy metadata to create the initial schema and upsert the fixture
participants. Before a real deployment, schema evolution should be moved to Alembic migrations.

View durable voice-call session history after configuring the same database URL:

```powershell
python -m orchestration.cli calls
```

## Automated tests

Run deterministic unit and webhook tests:

```powershell
.\scripts\run_tests.ps1
```

Run the same checks plus the real local PostgreSQL persistence test. This starts the repository's
Docker PostgreSQL container; it does not contact Twilio or Sarvam:

```powershell
.\scripts\run_tests.ps1 -WithPostgres
```

## Important simulation boundaries

- Free-form extraction is deterministic and intentionally conservative. It accepts facts only
  when a crop or number has enough nearby context, and it asks follow-ups for missing fields.
  It is not yet an evaluated production speech-understanding system.
- A middleman's maximum price is hidden simulator state. It is available in
  `python -m orchestration.cli show`
  for reviewers, but the negotiation algorithm never receives it as market evidence.
- Quotes are explicitly provisional. The workflow never creates a binding sale.
- Market observations and transport costs are synthetic fixtures.
- Ranking prefers risk-adjusted net return, not the largest headline price.

These boundaries are intentional. A later voice adapter can supply transcripts to the same
typed workflow without changing the negotiation and ranking contracts.
