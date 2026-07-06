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
    {"id": "debt_dpd0", "title": "Debt Collection — DPD0",
     "description": "Due-today reminder: neutral tone, block-account + credit-score consequence, single convincer.",
     "manifest_file": "debt_dpd0.yaml"},
    {"id": "debt_dpd1_5", "title": "Debt Collection — DPD 1-5",
     "description": "Firm mid-stage collector: greet+confirm, inform overdue, 2-tier convincer, collect PTP, multi-round KBs.",
     "manifest_file": "debt_collection_dpd1_5.yaml"},
    {"id": "debt_predue_d1", "title": "Debt Collection — Predue D-1",
     "description": "Softest pre-due reminder: gentle nudge, future-penalty framing, single convincer, give-more-time KB.",
     "manifest_file": "debt_predue_d1.yaml"},
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
