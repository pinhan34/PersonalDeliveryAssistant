## What this template defines
This spec template defines 4 main python tools for tracking the order status and return some information about them.

## Shared rules
- **TODAY = 2026-10-04.** The fake data is built around this date.
  Tools compare against this constant, never `datetime.now()`.
- **Bad input from the model** (unknown id / tracking number) →
  return {"error": "..."} so the model can recover.
- **Broken setup** (missing data file, malformed JSON) → let it raise.
  That is a programmer bug, not something the model can fix.

## identify_order
**Input:** query (str) — keywords extracted by the model, not the full user sentence
**Output:** list[dict] — each dict contains:
- order_id (str) — used by get_order in the next step
- items (list[str]) — shown to user for recognition
- order_date (str) — shown to user for disambiguation

**Deliberately excluded:** status, carrier, tracking_number,
expected_date — these come from get_order after confirmation.

**Matching:** query is split into words (punctuation dropped, hyphens
kept); words shorter than 3 letters and repeated words are ignored.
A word matches an order if it matches any of:
- order_id — exact, case-insensitive ("order-004")
- order_date — exact ISO date ("2026-09-28")
- weekday of order_date ("monday")
- item name — from the START of any word in the item, case-insensitive,
  ignoring spaces and hyphens, and may run on into the next words
  ("head" → "Headphones", "airfryer" → "Air Fryer", "usbc" → "USB-C").
  Not from the middle of a word: "air" does not match "Chair",
  "phones" does not match "Headphones".

**Ranking:** each order scores 1 point per matching word. Only the
orders with the highest score are returned ("monday charger": both
Monday orders match "monday", only the charger also matches "charger").
Ties are all returned, in file order ("monday" → 2 orders).
Assumes one query = one order; for several items the model should call
identify_order once per item.

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

**Input normalisation:** the number in the input decides the order, so
messy or short forms work: "order-004", " ORDER-004 ", "ORDER-4",
"ORDER004", "order 4", "004", "4" → ORDER-004.
Input without a number ("", "abc") → error.

**Unknown order_id:** return {"error": "..."} — do not raise. The message
says what IDs look like and points to identify_order, so the model can
recover instead of guessing another ID.

**Reads from:** data/orders.json

---

## track_package
**Input:** tracking_number (str)  
**Output:** dict containing:
- events (list of dicts: timestamp, location, status, note)
- status_classification (str) — one of:
  in_transit | out_for_delivery | delivered | stuck | 
  never_picked_up | at_depot

**Classification rules** — based on the LAST event (events[-1]).
Checked in this order, first match wins:

| # | Condition | Classification |
|---|-----------|----------------|
| 1 | last status == delivered | delivered |
| 2 | last status == out_for_delivery | out_for_delivery |
| 3 | last status == at_depot or delivery_attempted | at_depot |
| 4 | last status == label_created AND more than 3 days before TODAY | never_picked_up |
| 5 | last event is more than 3 days before TODAY | stuck |
| 6 | anything else | in_transit |

A fresh label_created (3 days or less) falls through to rule 6 →
in_transit: normal "waiting for pickup", not a problem yet.

Computed in a private helper `_classify_status(latest_event)` — called
with events[-1]; shared with
get_delivery_estimate so the rules live in one place.

**Input normalisation:** surrounding spaces are stripped and letters
uppercased (" tba000000000010 " → "TBA000000000010").

**Unknown tracking_number:** return {"error": "..."} — do not raise.
The model can recover from a wrong number; a crash ends the chat.
The message points to the tracking_number field of get_order (models
often pass the order_id by mistake) and mentions that a correct number
without events may mean the parcel never shipped or was cancelled.

**Reads from:** data/tracking.json

---

## get_delivery_estimate
**Input:** tracking_number (str)
**Output:** dict containing:
- expected_date (str) — the best current date (see reconciliation below)
- confidence (str) — one of: "high" | "medium" | "low" | "unknown"
- reason (str) — human-readable explanation of confidence level
- source (str) — "order" | "carrier_note" — who made this promise
- original_expected_date (str) — ONLY when source is "carrier_note":
  the orders.json date it replaced
- is_late (bool) — not delivered AND TODAY > expected_date

**Reconciliation — which date wins:**
- Primary source: expected_date from orders.json — always present
- Secondary source: note of the LAST tracking event — free text, unreliable
- Use the carrier note ONLY if it is an explicit reschedule — ALL of:
  - contains an ISO date (YYYY-MM-DD) — other formats are ignored
  - contains the word "scheduled" (also matches "rescheduled"),
    so unrelated dates ("duties must be paid by ...") are ignored
  - the date is not before TODAY, so stale carrier plans are ignored
  - the date differs from orders.json expected_date
  Then: expected_date = note date, source = "carrier_note",
  original_expected_date = orders.json date.
- Otherwise: expected_date = orders.json date, source = "order".

**Confidence rules** (uses `_classify_status`, same as track_package):
- "high"    → delivered or out_for_delivery
- "medium"  → in_transit AND not late
- "low"     → stuck, at_depot, OR in_transit AND late
- "unknown" → never_picked_up

**Moving vs late are separate questions:** status_classification says
whether the carrier is still scanning the parcel; is_late says whether
the promised date has passed. All four combinations exist in the data.

**Input normalisation:** same as track_package (strip + uppercase) —
the model passes the same tracking number to both tools.

**Errors:** unknown tracking_number → {"error": "..."} pointing to the
tracking_number field of get_order. Order exists but has no tracking
events → {"error": "..."} that includes the order status (e.g. cancelled).

**Reads from:** data/orders.json (expected_date) 
               + data/tracking.json (to determine confidence)

---

## Notes (tracking event `note` field)
- Not used for classification — free text, differs per carrier.
- Passed to the model unchanged inside track_package events; the model
  explains them to the user (reasons, required actions, deadlines).
- Only exception in code: an explicit ISO date for reconciliation above.
- Future: notes are a candidate for richer features (e.g. surfacing
  "customer action required" + deadlines) — decide when needed.