import agents
import samples


def test_registry_shape():
    listed = samples.list_samples()
    assert len(listed) == 3
    for e in listed:
        assert set(e) == {"id", "title", "description"}
    ids = {e["id"] for e in listed}
    assert ids == {"greeting_faq", "debt_collector", "appointment_booking"}


def test_every_sample_builds_clean():
    for entry in samples.SAMPLES:
        sid = entry["id"]
        manifest = samples.load_manifest(sid)
        assert manifest, f"{sid}: no manifest"
        built = agents.propose_build(manifest)
        assert built["ok"], f"{sid}: build failed: {built.get('error')}"
        errs = [f for f in agents.validate(built["proposed_data"]) if f["severity"] == "error"]
        assert errs == [], f"{sid}: error findings {errs}"


def test_load_manifest_and_title_unknown_id():
    assert samples.load_manifest("nope") is None
    assert samples.title_of("nope") is None
    assert samples.title_of("greeting_faq") == "Greeting & FAQ"
