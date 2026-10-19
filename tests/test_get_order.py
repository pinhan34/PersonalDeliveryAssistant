"""
Tests for get_order — derived from .claude/specs/tools.md.

Run:  python -m pytest tests/test_get_order.py -v
"""
import pytest

from agent.tools import get_order

# copied from data/orders.json — the exact record get_order must return
ORDER_004 = {
    "order_id": "ORDER-004",
    "items": ["IKEA MARKUS Office Chair"],
    "order_date": "2026-09-25",
    "expected_date": "2026-10-01",
    "carrier": "DHL",
    "tracking_number": "00340434161094000004",
    "status": "in_transit",
}


# --- Contract: shape of the return value ---------------------------------

def test_returns_full_record_for_exact_id():
    assert get_order("ORDER-004") == ORDER_004


def test_record_contains_all_fields():
    """get_order is the step that adds status, carrier and tracking_number."""
    assert set(get_order("ORDER-001").keys()) == {
        "order_id", "items", "order_date", "expected_date",
        "carrier", "tracking_number", "status",
    }


def test_unknown_id_returns_error_dict():
    """Unknown id -> {"error": ...}, never None, never an exception."""
    result = get_order("ORDER-999")
    assert isinstance(result, dict)
    assert "error" in result


# --- Error message helps the model recover -------------------------------

def test_error_message_points_to_identify_order():
    """The model reads this text and should switch to identify_order."""
    assert "identify_order" in get_order("ORDER-999")["error"]


# --- Your design decisions ------------------------------------------------

@pytest.mark.parametrize("order_id", [
    "order-004",        # lowercase
    "  ORDER-004 ",     # spaces around
    "ORDER-4",          # number not padded
    "ORDER004",         # no hyphen
    "order 4",          # how a user says it
    "004",              # number only
    "4",
])
def test_short_and_messy_ids_are_normalised(order_id):
    """Decision: any input whose number is 4 means ORDER-004."""
    assert get_order(order_id)["order_id"] == "ORDER-004"


@pytest.mark.parametrize("order_id", ["", "abc", "ORDER-"])
def test_ids_without_a_number_return_error(order_id):
    """No number to work with -> error dict, no crash."""
    assert "error" in get_order(order_id)
