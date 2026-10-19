import json, pathlib, datetime, re

DATA_DIR = pathlib.Path(__file__).parent.parent / "data"
TODAY = datetime.date(2026, 10, 4)   # the fake data is built around this date


def identify_order(query: str) -> list[dict]:
    """
    Find orders matching a keyword query.

    Each word (3+ letters) is matched against: order_id, order_date
    (e.g. "2026-09-28"), its weekday (e.g. "monday"), and item names.
    Case-insensitive; punctuation, spaces and hyphens are ignored for item
    names ("Kindle?" -> "kindle", "airfryer" / "air-fryer" -> "Air Fryer").
    Item words must match from the START of a word: "head" finds
    "Headphones", but "air" does not find "Chair".

    Orders are scored by how many words match; only the highest-scoring
    orders are returned ("monday charger" beats the other Monday order).

    Returns a list of {order_id, items, order_date}. Empty list if no match.
    """
    all_orders = _load_json_file(DATA_DIR / "orders.json")

    # "Kindle?" -> ["kindle"]; hyphens stay so "order-004" and "2026-09-28" survive
    words = re.findall(r"[a-z0-9-]+", query.lower())
    # drop short words and repeats: "my air air fryer" -> ["air", "fryer"]
    words = list(dict.fromkeys(w for w in words if len(_compact(w)) >= 3))
    matches = []

    for order in all_orders:
        # "2026-09-28" -> "monday"
        weekday = datetime.date.fromisoformat(order["order_date"]).strftime("%A").lower()
        # every item, read from each of its word starts (see _word_starts)
        starts = [start for item in order["items"] for start in _word_starts(item)]
        score = 0
        for word in words:
            if (
                word == order["order_id"].lower()
                or word == weekday
                or word == order["order_date"]
                or any(start.startswith(_compact(word)) for start in starts)
            ):
                score += 1

        if score > 0:  # matched at least one word
            matches.append(
                (score,
                {
                    "order_id": order["order_id"],
                    "items": order["items"],
                    "order_date": order["order_date"],
                }))

    if not matches:
        return []

    matches.sort(key=lambda x: x[0], reverse=True)  # highest score first; ties keep file order
    best_score = matches[0][0]
    return [m[1] for m in matches if m[0] == best_score]  # keep only the best matches

def get_order(order_id: str) -> dict:
    """
    Returns the full order record for an order_id. Short or messy forms
    work too ("order 4", "004", "ORDER-4" -> ORDER-004), see _normalize_order_id.
    Returns {"error": ...} if the order_id is not found.
    """
    all_orders = _load_json_file(DATA_DIR / "orders.json")
    order_id = _normalize_order_id(order_id)
    for order in all_orders:
        if order["order_id"] == order_id:
            return order
    return {"error": f"Order {order_id} not found. Order IDs look like ORDER-004. If unsure, use identify_order to search by item or date."}

def track_package(tracking_number: str) -> dict:
    """
    Returns a dict with {events, status_classification}.
    Returns {"error": "..."} if the tracking number is not found."""
    all_trackings = _load_json_file(DATA_DIR / "tracking.json")
    events = all_trackings.get(tracking_number.strip().upper())
    
    if not events:
        return {"error": f"No tracking data for {tracking_number} number found, Use the tracking_number field from get_order (not the order_id). If the number is correct, the parcel may not have shipped or the order may be cancelled — check status in get_order."}
    status = _classify_status(events[-1])
    track = {
        "events": events,
        "status_classification": status,
    }
    return track

def get_delivery_estimate(tracking_number: str) -> dict:
    """
    Returns {expected_date, confidence, reason, source, is_late}, plus
    original_expected_date when a carrier note rescheduled the delivery.
    Returns {"error": ...} if the order or its tracking is not found.
    """
    tracking_number = tracking_number.strip().upper()   # same normalisation as track_package
    all_orders = _load_json_file(DATA_DIR / "orders.json")
    order = next((o for o in all_orders if o["tracking_number"] == tracking_number), None)
    if not order:
        return {"error": f"No order with tracking number {tracking_number}. "
                         f"Use the tracking_number field from get_order (not the order_id)."}

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

def _compact(text: str) -> str:
    """
    Lowercases and removes spaces and hyphens, so differently written
    item names compare equal: "Air Fryer" / "air-fryer" -> "airfryer".
    """
    return text.lower().replace(" ", "").replace("-", "")

def _word_starts(item: str) -> list[str]:
    """
    The item name read from each of its word starts, without separators,
    so a query word can match the start of any word — even across spaces:
    "Philips Air Fryer XXL" -> ["philipsairfryerxxl", "airfryerxxl", "fryerxxl", "xxl"]
    """
    parts = [part for part in re.split(r"[^a-z0-9]+", item.lower()) if part]
    return ["".join(parts[i:]) for i in range(len(parts))]

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

def _normalize_order_id(order_id: str) -> str:
    """
    Uppercases and ensures the order ID starts with "ORDER-".
    """
    match = re.search(r"\d+", order_id, re.IGNORECASE)
    number = int(match.group()) if match else None
    if match and number is not None:
        return f"ORDER-{number:03d}"
    else:
        return order_id  # fallback if no number found


def _find_days_since_last_event(time_occurred: str) -> int:
    """
    Calculates the number of days between the event and TODAY.
    Raises if the timestamp is invalid — that is a bug in our data.
    """
    event_date = datetime.datetime.fromisoformat(time_occurred).date()
    return (TODAY - event_date).days