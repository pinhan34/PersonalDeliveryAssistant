"""
Tests for get_delivery_estimate — reconciliation rules from .claude/specs/tools.md.

Run:  python -m pytest -v
"""
from agent.tools import get_delivery_estimate


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
