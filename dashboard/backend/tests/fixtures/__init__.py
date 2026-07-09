import json
from pathlib import Path

FIXTURE_DIR = Path(__file__).resolve().parent
SAMPLE_EXPORT = FIXTURE_DIR / "sample_export.json"


def load_sample() -> dict:
    return json.loads(SAMPLE_EXPORT.read_text(encoding="utf-8"))


# A stable talk-node uuid present in the fixture (for read_node / node-text tests).
# Regenerate this if the manifest changes (builder uuids are content-seeded).
KNOWN_NODE_UUID = "fdce746c-fe23-5a51-a8b6-03654b1624fa"
