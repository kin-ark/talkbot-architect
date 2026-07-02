"""Curated starter-bot manifests for first-run onboarding (built on demand)."""
from __future__ import annotations

from pathlib import Path

_DIR = Path(__file__).parent

SAMPLES = [
    {"id": "greeting_faq", "title": "Greeting & FAQ",
     "description": "A minimal hello + goodbye flow — the simplest starting point.",
     "manifest_file": "greeting_faq.yaml"},
    {"id": "debt_collector", "title": "Debt Collection — Payment Reminder",
     "description": "Full collector flow: greet, confirm, inform, convince, collect commitment, handle cannot-pay + transfer, with business KBs.",
     "manifest_file": "debt_collection_payment_reminder.yaml"},
    {"id": "appointment_booking", "title": "Appointment Booking",
     "description": "Collects a choice, sets a variable, and routes on it.",
     "manifest_file": "appointment_booking.yaml"},
]

_BY_ID = {s["id"]: s for s in SAMPLES}


def list_samples() -> list[dict]:
    return [{"id": s["id"], "title": s["title"], "description": s["description"]} for s in SAMPLES]


def load_manifest(sample_id: str) -> str | None:
    entry = _BY_ID.get(sample_id)
    if entry is None:
        return None
    return (_DIR / entry["manifest_file"]).read_text(encoding="utf-8")


def title_of(sample_id: str) -> str | None:
    entry = _BY_ID.get(sample_id)
    return entry["title"] if entry else None
