import json, pathlib, datetime

DATA_DIR = pathlib.Path(__file__).parent.parent / "data"


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


def _load_json_file(file_path: pathlib.Path) -> list | dict:
    """
    Loads a JSON file. orders.json gives a list, tracking.json gives a dict.
    Raises if the file is missing or broken, so the bug is visible.
    """
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)