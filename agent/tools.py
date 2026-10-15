import json, pathlib, datetime, re

DATA_DIR = pathlib.Path(__file__).parent.parent / "data"
TODAY = datetime.date(2026, 10, 4)   # the fake data is built around this date


def identify_order(query: str) -> list[dict]:
    """
    Find orders matching a keyword query.

    Each word (3+ letters) is matched against: order_id, order_date
    (e.g. "2026-09-28"), its weekday (e.g. "monday"), and item names.
    Case-insensitive. Any matching word is enough (OR).

    Returns a list of {order_id, items, order_date}. Empty list if no match.
    """
    all_orders = _load_json_file(DATA_DIR / "orders.json")
    words = query.lower().split()
    matches = []
    for order in all_orders:
        # "2026-09-28" -> "monday"
        weekday = datetime.date.fromisoformat(order["order_date"]).strftime("%A").lower()
        items = [item.lower() for item in order["items"]]
        for word in words:
            if len(word) >= 3 and (
                word == order["order_id"].lower()
                or word == weekday
                or word == order["order_date"]
                or any(word in item for item in items)
            ):
                matches.append({
                    "order_id": order["order_id"],
                    "items": order["items"],
                    "order_date": order["order_date"],
                })
                break
    return matches

def get_order(order_id: str) -> dict:
    """
    Returns the full order record for an exact order_id (case-insensitive).
    Returns {"error": ...} if the order_id is not found.
    """
    all_orders = _load_json_file(DATA_DIR / "orders.json")
    for order in all_orders:
        if order["order_id"] == order_id.strip().upper():
            return order
    return {"error": f"Order {order_id} not found."}

def track_package(tracking_number: str) -> dict:
    """
    Returns a dict with {events, status_classification}.
    Returns {"error": "..."} if the tracking number is not found."""
    all_trackings = _load_json_file(DATA_DIR / "tracking.json")
    order_tracked = all_trackings.get(tracking_number)
    
    if not order_tracked:
        return {"error": f"Tracking number {tracking_number} not found."}
    status = _classify_status(order_tracked[-1])
    track = {
          "events": order_tracked,
          "status_classification": status,
     }
    return track

def get_delivery_estimate(tracking_number: str) -> dict:
    """
    Returns {expected_date, confidence, reason, source, is_late}, plus
    original_expected_date when a carrier note rescheduled the delivery.
    Returns {"error": ...} if the order or its tracking is not found.
    """
    all_orders = _load_json_file(DATA_DIR / "orders.json")
    order = next((o for o in all_orders if o["tracking_number"] == tracking_number), None)
    if not order:
        return {"error": f"No order with tracking number {tracking_number}."}

    events = _load_json_file(DATA_DIR / "tracking.json").get(tracking_number)
    if not events:
        return {"error": f"No tracking data for {tracking_number} "
                         f"(order status: {order['status']})."}

    latest_event = events[-1]
    status = _classify_status(latest_event)

    # Which date wins: the order's date, unless the carrier note is an explicit reschedule
    estimate = {"expected_date": order["expected_date"], "source": "order"}
    note = latest_event["note"] or ""
    note_date = re.search(r"\d{4}-\d{2}-\d{2}", note)
    if (
        note_date
        and "scheduled" in note.lower()   # also matches "rescheduled"
        and datetime.date.fromisoformat(note_date.group()) >= TODAY
        and note_date.group() != order["expected_date"]
    ):
        estimate = {
            "expected_date": note_date.group(),
            "source": "carrier_note",
            "original_expected_date": order["expected_date"],
        }

    is_late = status != "delivered" and TODAY > datetime.date.fromisoformat(estimate["expected_date"])

    if status in ("delivered", "out_for_delivery"):
        confidence, reason = "high", f"Package is {status}."
    elif status == "in_transit" and not is_late:
        confidence, reason = "medium", "Package is moving and on schedule."
    elif status == "in_transit":
        confidence, reason = "low", "Package is moving but the expected date has passed."
    elif status in ("stuck", "at_depot"):
        confidence, reason = "low", f"Package is {status}: no progress towards delivery."
    else:  # never_picked_up
        confidence, reason = "unknown", "Carrier has not received the package yet."

    return {**estimate, "confidence": confidence, "reason": reason, "is_late": is_late}

def _load_json_file(file_path: pathlib.Path) -> list | dict:
    """
    Loads a JSON file. orders.json gives a list, tracking.json gives a dict.
    Raises if the file is missing or broken, so the bug is visible.
    """
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)

def _classify_status(latest_event: dict) -> str:
    """
    Classifies a package from its latest tracking event (rules in tools.md).
    Returns one of: "delivered", "out_for_delivery", "at_depot",
    "never_picked_up", "stuck", "in_transit".
    """
    status = latest_event["status"]
    days = _find_days_since_last_event(latest_event["timestamp"])
    if status == "delivered":
        return "delivered"
    elif status == "out_for_delivery":
        return "out_for_delivery"
    elif status == "at_depot" or status == "delivery_attempted":
        return "at_depot"
    elif status == "label_created" and days > 3:
        return "never_picked_up"
    elif days > 3:
        return "stuck"
    else:
        return "in_transit"


def _find_days_since_last_event(time_occurred: str) -> int:
    """
    Calculates the number of days between the event and TODAY.
    Raises if the timestamp is invalid — that is a bug in our data.
    """
    event_date = datetime.datetime.fromisoformat(time_occurred).date()
    return (TODAY - event_date).days