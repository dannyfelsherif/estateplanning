"""Thin wrapper around the Claude API for the three AI-assisted workflows:
client summarization, document extraction, drafting, and risk analysis.

All prompts are explicit that outputs are drafts for a licensed attorney to
review — the wrapper never claims to give legal advice, and callers must
keep the human-in-the-loop status gates (see app/models.py DraftStatus).

If no API key is configured, every function returns a clearly labeled mock
response so the rest of the app can be built/demoed/tested without a key.
"""

import json

from app.config import settings

MOCK_TAG = "[MOCK LLM OUTPUT — set ANTHROPIC_API_KEY in .env for real generation]"

_client = None


def _get_client():
    global _client
    if _client is None:
        import anthropic

        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


def _call(system: str, user_prompt: str, max_tokens: int = 2000) -> str:
    if settings.mock_llm:
        return f"{MOCK_TAG}\n\n(This would normally be generated from the prompt below.)\n\n{user_prompt[:600]}"

    client = _get_client()
    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_prompt}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def _call_json(system: str, user_prompt: str, max_tokens: int = 2000) -> dict:
    if settings.mock_llm:
        return {
            "mock": True,
            "note": MOCK_TAG,
            "raw_prompt_excerpt": user_prompt[:600],
        }

    raw = _call(system + "\n\nRespond with ONLY valid JSON, no prose, no markdown fences.", user_prompt, max_tokens)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "parse_error": True,
            "raw_response": raw,
            "note": "Model did not return valid JSON; a human must review the raw response.",
        }


SUMMARY_SYSTEM = (
    "You are an intake assistant for a licensed estate planning law firm. "
    "You turn raw client intake data into a concise, structured summary for "
    "the supervising attorney. You do not give legal advice, recommend "
    "specific legal strategies, or draw legal conclusions. Flag anything "
    "that looks incomplete or contradictory instead of guessing."
)


def generate_client_summary(client_data: dict) -> str:
    prompt = (
        "Summarize the following client intake data for the attorney's file. "
        "Organize into: Family Situation, Assets Overview, Stated Goals, and "
        "Open Questions / Missing Information. Be factual, do not speculate "
        "beyond the given data.\n\n" + json.dumps(client_data, indent=2, default=str)
    )
    return _call(SUMMARY_SYSTEM, prompt)


DOCUMENT_EXTRACTION_SYSTEM = (
    "You are a document-review assistant for a licensed estate planning law "
    "firm. You extract structured facts from legacy estate planning and "
    "financial documents. You do not give legal advice or opinions on "
    "validity or enforceability — only the supervising attorney determines "
    "that. If something is unclear or illegible, say so instead of guessing."
)


def summarize_document(raw_text: str, doc_type: str) -> dict:
    prompt = (
        f"Document type (as classified by the uploader): {doc_type}\n\n"
        "Extract the following as JSON with keys: "
        "'parties' (list of names/roles found, e.g. testator, executor, agent, trustee), "
        "'beneficiaries' (list of {name, share_or_asset} as stated in the document), "
        "'key_dates' (list of {label, date}), "
        "'clauses_present' (list of clause types found, e.g. residuary clause, guardianship clause, "
        "no-contest clause, witness/notary block), "
        "'plain_summary' (2-4 sentence plain-English summary), "
        "'potential_issues' (list of strings noting anything ambiguous, contradictory, or incomplete "
        "that an attorney should double check).\n\n"
        "Document text:\n" + raw_text[:12000]
    )
    return _call_json(DOCUMENT_EXTRACTION_SYSTEM, prompt)


DRAFTING_SYSTEM = (
    "You are a drafting assistant for a licensed estate planning law firm. "
    "You fill in the firm's vetted document template using the client data "
    "provided, following the template's structure and clause order exactly. "
    "You do not add, remove, or reinterpret substantive legal clauses beyond "
    "filling in bracketed placeholders and clearly-templated repeating "
    "sections (e.g. one paragraph per beneficiary). If required client data "
    "is missing for a placeholder, leave the placeholder as "
    "'[ATTORNEY INPUT NEEDED: <what is missing>]' rather than inventing "
    "content. This is a first-pass draft only — it is not legal advice and "
    "is not valid for execution until a licensed attorney reviews and "
    "approves it."
)


def draft_document(doc_type: str, template_text: str, client_data: dict) -> str:
    prompt = (
        f"Document type: {doc_type}\n\n"
        "Firm template (follow this structure exactly, filling in placeholders):\n"
        "-----\n" + template_text + "\n-----\n\n"
        "Client data (JSON):\n" + json.dumps(client_data, indent=2, default=str) + "\n\n"
        "Produce the filled-in draft text only, ready to hand to the attorney for review."
    )
    return _call(DRAFTING_SYSTEM, prompt, max_tokens=3000)


RISK_SYSTEM = (
    "You are a risk-review assistant for a licensed estate planning law "
    "firm. You review draft or existing estate planning documents for "
    "missing clauses, conflicting beneficiary designations, ambiguous "
    "distribution language, and execution-formality gaps (signatures, "
    "witnesses, notarization). You flag issues for a licensed attorney to "
    "resolve — you never resolve them yourself and never give legal advice "
    "about which outcome is correct."
)


def analyze_risks(text: str, context: dict) -> list[dict]:
    prompt = (
        "Review the document text below along with the client context and "
        "return JSON: {\"flags\": [{\"category\": one of "
        "['missing_clause','conflicting_beneficiary','ambiguous_distribution',"
        "'execution_formality','other'], \"severity\": one of "
        "['low','medium','high'], \"description\": string}]}. "
        "Only include real, specific issues grounded in the text/context — "
        "return an empty list if you find none.\n\n"
        "Client context (JSON):\n" + json.dumps(context, indent=2, default=str) + "\n\n"
        "Document text:\n" + text[:12000]
    )
    result = _call_json(RISK_SYSTEM, prompt)
    if isinstance(result, dict) and isinstance(result.get("flags"), list):
        return result["flags"]
    return []
