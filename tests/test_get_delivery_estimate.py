"""
Tests for get_delivery_estimate — reconciliation rules from .claude/specs/tools.md.

Run:  python -m pytest -v
"""
import pytest

from agent.tools import get_delivery_estimate


# --- Contract: shape of the return value ---------------------------------

def test_returns_all_fields_for_normal_order():
    """No carrier reschedule -> no original_expected_date key."""
    result = get_delivery_estimate("00340434161094000001")
    assert set(result.keys()) == {"expected_date", "confidence", "reason", "source", "is_late"}


# --- Which date wins: order vs carrier note ------------------------------

def test_carrier_reschedule_wins():
    """ORDER-008: note 'Delivery rescheduled to 2026-10-06' replaces 2026-10-05."""
    result = get_delivery_estimate("00340434161094000008")
    assert result["expected_date"] == "2026-10-06"
    assert result["source"] == "carrier_note"
    assert result["original_expected_date"] == "2026-10-05"


def test_note_with_same_date_keeps_order():
    """ORDER-002: note confirms the order date, so nothing is rescheduled."""
    result = get_delivery_estimate("01505000000002")
    assert result["expected_date"] == "2026-10-05"
    assert result["source"] == "order"
    assert "original_expected_date" not in result


def test_date_without_scheduled_keyword_is_ignored():
    """ORDER-014: 'duties must be paid by 2026-10-09' is a deadline, not a delivery date."""
    result = get_delivery_estimate("00340434161094000014")
    assert result["expected_date"] == "2026-10-06"
    assert result["source"] == "order"


def test_past_scheduled_date_is_ignored():
    """ORDER-015: 'Scheduled for delivery 2026-10-02' is before TODAY — a stale plan."""
    result = get_delivery_estimate("01505000000015")
    assert result["expected_date"] == "2026-10-01"
    assert result["source"] == "order"
    assert result["is_late"] is True


# --- Errors ---------------------------------------------------------------

def test_cancelled_order_without_tracking_returns_error():
    """ORDER-013: no tracking entry — error dict mentions the order status."""
    result = get_delivery_estimate("01505000000013")
    assert "error" in result
    assert "cancelled" in result["error"]


def test_unknown_tracking_number_returns_error():
    result = get_delivery_estimate("NOT-A-REAL-NUMBER")
    assert "error" in result


def test_order_id_by_mistake_points_to_get_order():
    """Classic mix-up: model passes the order_id instead of the tracking_number."""
    assert "get_order" in get_delivery_estimate("ORDER-006")["error"]


# --- Confidence rules (tools.md) ------------------------------------------

@pytest.mark.parametrize("tracking_number, expected", [
    ("00340434161094000003", "high"),      # delivered — Kindle
    ("TBA000000000010",      "high"),      # out_for_delivery — Echo Dot
    ("00340434161094000001", "medium"),    # in_transit, not late — headphones
    ("01505000000009",       "low"),       # in_transit but late — charger
    ("00340434161094000004", "low"),       # stuck — chair
    ("01505000000006",       "low"),       # at_depot — air fryer
    ("01505000000005",       "unknown"),   # never_picked_up — yoga mat
])
def test_confidence(tracking_number, expected):
    assert get_delivery_estimate(tracking_number)["confidence"] == expected


# --- Moving vs late are separate questions --------------------------------

@pytest.mark.parametrize("tracking_number, expected_late", [
    ("00340434161094000001", False),   # moving, on time   — headphones
    ("01505000000009",       True),    # moving, late      — charger
    ("00340434161094000011", False),   # stuck, on time    — jacket (customs)
    ("00340434161094000004", True),    # stuck, late       — chair
])
def test_is_late_is_independent_of_movement(tracking_number, expected_late):
    assert get_delivery_estimate(tracking_number)["is_late"] is expected_late


def test_delivered_is_never_late():
    """Kindle: expected 2026-09-27 is before TODAY, but it was delivered -> not late."""
    assert get_delivery_estimate("00340434161094000003")["is_late"] is False


# --- Your design decisions ------------------------------------------------

@pytest.mark.parametrize("tracking_number", [
    " 01505000000006 ",     # spaces around
    "tba000000000010",      # lowercase letters
])
def test_messy_input_is_normalised(tracking_number):
    """Same normalisation as track_package — the model passes the same number to both."""
    assert "confidence" in get_delivery_estimate(tracking_number)
