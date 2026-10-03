## What this template defines
This spec template defines 4 main python tools for tracking the order status and return some information about them.

## identify_order
**Input:** query (str) — raw natural language from the user
**Output:** list[dict] — each dict contains:
- order_id (str) — used by get_order in the next step
- items (list[str]) — shown to user for recognition
- order_date (str) — shown to user for disambiguation

**Deliberately excluded:** status, carrier, tracking_number,
expected_date — these come from get_order after confirmation.

**Behaviour:**
- Returns empty list if no match
- Returns multiple dicts if ambiguous  
- Never returns None

**Reads from:** data/orders.json

---

## get_order
**Input:** order_id (str)  
**Output:** dict containing:
- order_id, items (list[str]), order_date, expected_date, 
  carrier, tracking_number, status

**Reads from:** data/orders.json

---

## track_package
**Input:** tracking_number (str)  
**Output:** dict containing:
- events (list of dicts: timestamp, location, status, note)
- status_classification (str) — one of:
  in_transit | out_for_delivery | delivered | stuck | 
  never_picked_up | at_depot

**Reads from:** data/tracking.json

---

## get_delivery_estimate
**Input:** tracking_number (str)
**Output:** dict containing:
- expected_date (str) — from orders.json expected_date field
- confidence (str) — one of: "high" | "medium" | "low" | "unknown"
- reason (str) — human-readable explanation of confidence level

**Confidence rules:**
- "high"    → status_classification is out_for_delivery or delivered
- "medium"  → status_classification is in_transit, on schedule
- "low"     → status_classification is stuck or at_depot
- "unknown" → status_classification is never_picked_up

**Reads from:** data/orders.json (expected_date) 
               + data/tracking.json (to determine confidence)

**Reads from:** data/orders.json