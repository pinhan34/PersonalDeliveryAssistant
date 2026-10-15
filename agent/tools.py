import json, pathlib, datetime

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