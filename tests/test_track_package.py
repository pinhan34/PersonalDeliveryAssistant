"""
Tests for track_package — derived from .claude/specs/tools.md.
TODAY is fixed at 2026-10-04, so the classifications below never change.

Run:  python -m pytest tests/test_track_package.py -v
"""
import json
import pathlib

import pytest

from agent.tools import track_package

# read the raw data directly, so a bug in tools.py can't hide in the expected values
TRACKING = json.loads(
    (pathlib.Path(__file__).parent.parent / "data" / "tracking.json").read_text(encoding="utf-8")
)


# --- Contract: shape of the return value ---------------------------------

def test_returns_events_and_classification_only():
    result = track_package("00340434161094000001")
    assert set(result.keys()) == {"events", "status_classification"}


def test_events_are_returned_unchanged():
    """All events, same order, notes untouched — the model explains them."""
    assert track_package("01505000000006")["events"] == TRACKING["01505000000006"]


def test_latest_note_reaches_the_model():
    """Air fryer: the action + deadline note must not be dropped."""
    last_note = track_package("01505000000006")["events"][-1]["note"]
    assert "customer action required" in last_note


# --- Classification rules (tools.md table, first match wins) -------------

@pytest.mark.parametrize("tracking_number, expected", [
    ("00340434161094000003", "delivered"),          # rule 1 — Kindle
    ("TBA000000000010",      "out_for_delivery"),   # rule 2 — Echo Dot
    ("01505000000006",       "at_depot"),           # rule 3 — air fryer
    ("01505000000005",       "never_picked_up"),    # rule 4 — label 11 days old
    ("00340434161094000004", "stuck"),              # rule 5 — last scan 5 days ago
    ("00340434161094000011", "stuck"),              # rule 5 — customs, 4 days ago
    ("01505000000009",       "in_transit"),         # rule 6 — recent scan
])
def test_classification(tracking_number, expected):
    assert track_package(tracking_number)["status_classification"] == expected


def test_fresh_label_is_not_never_picked_up():
    """Label created 2 days ago (<= 3) falls through to in_transit, not a problem yet."""
    assert track_package("H1000000000012")["status_classification"] == "in_transit"


# --- Errors: the model must be able to recover ---------------------------

def test_unknown_tracking_number_returns_error():
    result = track_package("99999999999999")
    assert isinstance(result, dict)
    assert "error" in result


def test_order_id_by_mistake_points_to_get_order():
    """Classic mix-up: model passes the order_id instead of the tracking_number."""
    assert "get_order" in track_package("ORDER-006")["error"]


def test_cancelled_order_has_no_tracking():
    """ORDER-013 was cancelled: its tracking number has no events -> error, not a crash."""
    assert "error" in track_package("01505000000013")


# --- Your design decisions ------------------------------------------------

@pytest.mark.parametrize("tracking_number", [
    " 01505000000006 ",     # spaces around
    "tba000000000010",      # lowercase letters
])
def test_messy_input_is_normalised(tracking_number):
    assert "events" in track_package(tracking_number)
