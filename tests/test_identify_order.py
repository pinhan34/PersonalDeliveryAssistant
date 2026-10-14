"""
Tests for identify_order — derived from .claude/specs/tools.md.

Each test fails with NotImplementedError until you fill it in.
Replace the `raise` line with your call + asserts.

Run:  python -m pytest -v
"""
import pytest

from agent.tools import identify_order


# --- Contract: shape of the return value ---------------------------------

def test_returns_list_for_single_match():
    """Even one match must come back as a list, not a bare dict."""
    result = identify_order("headphones")
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["order_id"] == "ORDER-001"


def test_returns_empty_list_for_no_match():
    """No match -> [] (never None, never an error dict)."""
    result = identify_order("definitely-not-a-real-item")
    assert result == []


def test_result_contains_only_allowed_fields():
    """Each dict has exactly order_id, items, order_date — no status, carrier, etc."""
    result = identify_order("headphones")
    assert result
    assert set(result[0].keys()) == {"order_id", "items", "order_date"}


# --- Matching behaviour ---------------------------------------------------

def test_matches_by_item_name():
    """'headphones' should find the Sony order."""
    result = identify_order("headphones")
    assert [entry["order_id"] for entry in result] == ["ORDER-001"]


def test_matching_ignores_case():
    """'KINDLE' and 'kindle' should both find the Kindle order."""
    assert identify_order("KINDLE") == [{"order_id": "ORDER-003", "items": ["Kindle Paperwhite"], "order_date": "2026-09-24"}]
    assert identify_order("kindle") == [{"order_id": "ORDER-003", "items": ["Kindle Paperwhite"], "order_date": "2026-09-24"}]


def test_matches_by_order_id():
    """'ORDER-004' should return that order."""
    result = identify_order("ORDER-004")
    assert result == [{"order_id": "ORDER-004", "items": ["IKEA MARKUS Office Chair"], "order_date": "2026-09-25"}]


def test_monday_returns_multiple_orders():
    """'Monday' — the CLAUDE.md example. More than one order was placed on a Monday."""
    result = identify_order("Monday")
    assert {entry["order_id"] for entry in result} == {"ORDER-008", "ORDER-009"}


# --- Your design decisions ------------------------------------------------
# These have no "right" answer in the spec. Decide, then write the test.

@pytest.mark.parametrize("query", ["", "   "])
def test_blank_query(query):
    """What should an empty / whitespace-only query return? Everything? Nothing?"""
    assert identify_order(query) == []


def test_partial_word():
    """Should 'head' match 'Headphones'? Should 'air' match 'Air Fryer' AND 'Office Chair'?"""
    assert identify_order("head") == [{"order_id": "ORDER-001", "items": ["Sony WH-1000XM5 Headphones"], "order_date": "2026-09-30"}]
    assert {entry["order_id"] for entry in identify_order("air")} == {"ORDER-004", "ORDER-006"}
