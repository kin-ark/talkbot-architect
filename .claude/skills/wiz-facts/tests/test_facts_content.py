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


def test_required_intent_is_unclassified():
    facts = load_facts()
    assert facts.get("intent.required") == ["Unclassified"]


def test_node_labels_include_seed_set():
    facts = load_facts()
    labels = set(facts.get("vocabulary.node_labels"))
    assert {"Greeting", "Pitch", "Closing"} <= labels
