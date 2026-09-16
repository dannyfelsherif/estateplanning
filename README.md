# AI Estate Planning Agent

A workflow tool that helps a licensed estate planning practice move faster
through intake, document review, and first-draft generation — **without**
ever putting an AI in charge of a legal or strategic decision. Every
AI-generated output is a draft. Nothing reaches a client until a licensed
attorney has reviewed and approved it.

> **This is not a law firm and does not provide legal advice.** It is
> internal tooling meant to be operated by, or under the direct supervision
> of, a licensed attorney. See [`docs/SECURITY_CHECKLIST.md`](docs/SECURITY_CHECKLIST.md)
> for the transparency/security posture of this MVP and what's still needed
> before handling real client PII in production.

## Core capabilities

1. **Intake & discovery** — structured forms capture family members, assets,
   and client goals. A one-click "Generate Summary" turns that raw intake
   into a structured advisor-facing summary (via Claude).
2. **Document parsing & summarization** — upload legacy wills, trusts, or
   financial statements (PDF/TXT); the app extracts text and asks Claude to
   summarize key parties, clauses, beneficiaries, and dates into structured
   data an advisor can scan in seconds.
3. **Drafting first passes** — generates a first-draft Will, Financial POA,
   Healthcare POA, or HIPAA Authorization from vetted firm templates
   (`app/templates_lib/`) merged with the client's intake data. Every draft
   is watermarked `DRAFT — PENDING ATTORNEY REVIEW — NOT FOR EXECUTION` and
   starts in `draft` status; it cannot become `approved` or `finalized`
   except by a user with the `attorney` role.
4. **Risk & error flagging** — rule-based checks (missing signature/witness
   blocks, missing residuary or guardianship clauses, beneficiary
   designations that don't match intake data) plus an LLM pass for
   ambiguous distribution language, run against both new drafts and
   uploaded legacy documents.

Every create/update/approve/finalize action is written to an append-only
`audit_log` table with the acting user, timestamp, and action.

## Architecture

- **Backend:** FastAPI + SQLAlchemy (SQLite for the MVP).
- **Frontend:** server-rendered Jinja2 templates with small vanilla-JS
  fetch calls for uploads and generation actions — no build step required.
- **LLM:** Anthropic Claude, called only for summarization/drafting/risk
  text generation. If `ANTHROPIC_API_KEY` is unset, the app runs in
  `MOCK_LLM` mode: every AI output is a clearly labeled stub so you can
  demo the full workflow without an API key or real client data.
- **Auth:** email/password with bcrypt hashing, signed session cookies,
  two roles (`attorney`, `paralegal`). Approval/finalization actions are
  gated to `attorney`.

## Getting started

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # fill in ANTHROPIC_API_KEY, SESSION_SECRET_KEY, admin creds
python scripts/seed.py  # creates the first attorney account and the DB tables
uvicorn app.main:app --reload
```

Visit http://127.0.0.1:8000, log in with the admin credentials from `.env`,
and create your first client.

Run tests with:

```bash
pytest
```

## Data flow / third-party disclosure

Client intake data, uploaded document text, and draft text are sent to the
Anthropic API when generating summaries, extractions, drafts, or risk
analysis (unless `MOCK_LLM` mode is active). No other third party receives
this data. Per Anthropic's API terms, API inputs/outputs are not used to
train models by default. Review your firm's data processing agreements and
applicable state bar guidance on AI use before processing real client PII.

## Project layout

```
app/
  main.py              FastAPI app + route registration
  config.py            settings (env-driven)
  db.py                SQLAlchemy engine/session
  models.py            ORM models
  security.py          auth, sessions, roles, audit logging
  llm.py               Claude client wrapper (+ mock fallback)
  services/            intake, document parsing, drafting, risk flagging
  templates_lib/       vetted firm document templates
  routers/             HTTP route handlers
  templates/           Jinja2 HTML
  static/              CSS
docs/SECURITY_CHECKLIST.md   transparency/security self-assessment
scripts/seed.py               first-run admin/user + DB bootstrap
tests/                         unit tests for risk flagging & drafting
```
