"""Curated starter-bot manifests for first-run onboarding (built on demand)."""
from __future__ import annotations

from pathlib import Path

_DIR = Path(__file__).parent

SAMPLES = [
    {"id": "greeting_faq", "title": "Greeting & FAQ",
     "description": "A minimal hello + goodbye flow — the simplest starting point.",
     "manifest_file": "greeting_faq.yaml"},
    {"id": "debt_collector", "title": "Debt Collection (Starter)",
     "description": "Recommended starting point — the canonical mid-funnel collector (DPD 1-5): greet+confirm, inform overdue, 2-tier convincer, collect PTP, ~16 corpus intents + multi-round business KBs + disposition tags.",
     "manifest_file": "debt_collection_dpd1_5.yaml"},
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
    {"id": "debt_dpd6_30", "title": "Debt Collection — DPD 6-30",
     "description": "Insistent overdue collector: overdue-days framing, accruing-penalty consequence, 3-tier convincer, DPD info KB.",
     "manifest_file": "debt_dpd6_30.yaml"},
    {"id": "debt_overdue_90", "title": "Debt Collection — Overdue 90+",
     "description": "Long-overdue collector: escalating repetition, randomized convincer variants, 3-tier ladder, keringanan/restructuring KB.",
     "manifest_file": "debt_overdue_90.yaml"},
    {"id": "debt_ptp_reminder", "title": "Debt Collection — PTP Reminder",
     "description": "Promise-to-pay follow-up: janji-bayar framing, reason-classified convincer fan-out, re-collect PTP time + method, strongest pressure.",
     "manifest_file": "debt_ptp_reminder.yaml"},
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
