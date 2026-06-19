from wizfacts import load_facts


def test_supported_languages_present():
    facts = load_facts()
    assert set(facts.get("lang.supported")) == {"ZHO", "ENG", "IDN", "THA"}


def test_global_hotword_constraint_present():
    facts = load_facts()
    assert set(facts.get("lang.global_hotword_unsupported")) == {"ZHO", "THA"}


def test_every_fact_has_nonempty_quote_and_pages():
    facts = load_facts()
    for fid in ["lang.supported", "lang.global_hotword_unsupported"]:
        cite = facts.cite(fid)
        assert cite["pages"], f"{fid} missing pages"
