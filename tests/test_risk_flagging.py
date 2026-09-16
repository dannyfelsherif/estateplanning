from app.services.risk_flagging import _rule_checks_draft

CLEAN_CONTENT = """
LAST WILL AND TESTAMENT OF Jane Doe

ARTICLE V — RESIDUARY CLAUSE
I give all the rest of my estate to my spouse, John Doe.

WITNESS BLOCK
Signature: ______
""".strip()

CLEAN_CLIENT_DATA = {
    "family_members": [
        {"name": "John Doe", "relationship": "spouse", "is_dependent": False},
    ],
    "assets": [
        {"description": "Checking account", "beneficiary_designation": "John Doe"},
    ],
}


def test_clean_draft_has_no_flags():
    flags = _rule_checks_draft(CLEAN_CONTENT, CLEAN_CLIENT_DATA)
    assert flags == []


def test_unresolved_attorney_placeholder_flagged():
    content = CLEAN_CONTENT + "\n[ATTORNEY INPUT NEEDED: guardian name]"
    flags = _rule_checks_draft(content, CLEAN_CLIENT_DATA)
    categories = {f["category"] for f in flags}
    assert "missing_clause" in categories
    assert any(f["severity"] == "high" for f in flags)


def test_leftover_template_placeholder_flagged():
    content = CLEAN_CONTENT + "\nGuardian: [GUARDIAN NAME]"
    flags = _rule_checks_draft(content, CLEAN_CLIENT_DATA)
    assert any(f["category"] == "missing_clause" for f in flags)


def test_missing_guardian_for_dependent_flagged():
    client_data = {
        "family_members": [{"name": "Kid Doe", "relationship": "child", "is_dependent": True}],
        "assets": [],
    }
    flags = _rule_checks_draft(CLEAN_CONTENT, client_data)
    assert any(
        f["category"] == "missing_clause" and f["severity"] == "high" and "guardian" in f["description"].lower()
        for f in flags
    )


def test_conflicting_beneficiary_flagged():
    client_data = {
        "family_members": [],
        "assets": [{"description": "Brokerage account", "beneficiary_designation": "Someone Else"}],
    }
    flags = _rule_checks_draft(CLEAN_CONTENT, client_data)
    assert any(f["category"] == "conflicting_beneficiary" for f in flags)


def test_ambiguous_language_flagged():
    content = CLEAN_CONTENT + "\nDistribute some of my belongings as appropriate."
    flags = _rule_checks_draft(content, CLEAN_CLIENT_DATA)
    assert any(f["category"] == "ambiguous_distribution" for f in flags)


def test_missing_execution_block_flagged():
    content = "LAST WILL AND TESTAMENT OF Jane Doe\n\nI leave everything to my spouse."
    flags = _rule_checks_draft(content, CLEAN_CLIENT_DATA)
    assert any(f["category"] == "execution_formality" and f["severity"] == "high" for f in flags)
