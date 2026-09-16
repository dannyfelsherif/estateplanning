# AI Estate Planning Software Checklist

A self-assessment against the standard criteria a firm should apply before
trusting any AI estate planning tool with real client data. Status reflects
this MVP as committed; items marked "Planned" are known gaps to close
before production use with real client PII.

## Data security

| Item | Status | Notes |
|---|---|---|
| Encryption in transit | Implemented | Deploy behind HTTPS/TLS (e.g. behind a reverse proxy). The app itself does not terminate TLS. |
| Encryption at rest | Planned | MVP uses a local SQLite file and local disk for uploads, unencrypted. Production should use an encrypted volume/DB (e.g. RDS with encryption, or SQLCipher) and encrypted object storage for documents. |
| Secrets management | Implemented | API keys and session secret are read from environment variables (`.env`, gitignored), never hardcoded or committed. |
| Access control (RBAC) | Implemented | Two roles (`attorney`, `paralegal`); approval/finalization of legal documents and resolving risk flags are attorney-only. |
| Session security | Implemented | Signed, `httponly`, `samesite=lax` session cookies with a 12-hour expiry. |
| Password storage | Implemented | bcrypt via passlib; no plaintext passwords stored. |
| Least-privilege data sharing with third parties | Implemented | Only Anthropic's API receives client data, and only for the specific summarization/drafting/risk-analysis calls described in the README. No analytics or ad-tech third parties are integrated. |

## Transparency & human oversight

| Item | Status | Notes |
|---|---|---|
| Human-in-the-loop gate before anything is "final" | Implemented | `Draft.status` workflow: `draft` → `under_review` → `approved` → `finalized`. Only an `attorney`-role user can move a draft to `approved` or `finalized`. |
| Clear AI-generated-content labeling | Implemented | Every generated draft is watermarked "DRAFT — PENDING ATTORNEY REVIEW — NOT FOR EXECUTION" and the UI shows a persistent disclaimer banner on every page. |
| No autonomous legal conclusions | Implemented | LLM system prompts explicitly instruct the model not to give legal advice or resolve ambiguities — it only extracts, drafts from templates, and flags issues for attorney judgment. |
| Audit trail | Implemented | Every create/update/generate/approve/resolve action is written to an append-only `audit_log` table with actor, timestamp, and action. |
| Explainability of risk flags | Implemented | Each risk flag records its category, severity, and a plain-language description; rule-based flags are traceable to a specific check, LLM flags are traceable to the source document/draft. |

## Legal / compliance

| Item | Status | Notes |
|---|---|---|
| Unauthorized practice of law (UPL) guardrails | Implemented (process) | Tool is positioned as internal firm tooling operated by/under a licensed attorney, not a consumer-facing legal service. Confirm this posture against your state bar's rules on AI use before any client-facing deployment. |
| Jurisdiction awareness | Partial | Client records capture a governing `state`, and templates include jurisdiction-dependent placeholders (execution formalities, gifting limits), but the app does not yet enforce state-specific legal rules automatically — attorney review must confirm jurisdiction-specific requirements. |
| Data retention & deletion | Planned | No automated retention/deletion policy yet. Add one before storing real client PII long-term. |
| Client consent / data processing disclosure | Planned | Add a client-facing notice describing that AI tools assist drafting and that a licensed attorney reviews all output, per applicable state bar guidance. |
| Vendor subprocessor disclosure | Implemented | Documented in README: Anthropic is the only subprocessor receiving client data, and only for LLM calls described above. |

## Before production use with real client data

1. Move off local SQLite/local disk to encrypted managed storage.
2. Put the app behind TLS and a real authentication provider (SSO/MFA) if used beyond a single small team.
3. Add data retention/deletion policy and backups.
4. Confirm state bar guidance on AI-assisted drafting for your jurisdiction(s).
5. Add a formal incident response plan for any data exposure involving client PII.
