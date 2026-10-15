## Design decision — shipments
V1 assumes one shipment per order (one carrier, one tracking number).
Real Amazon orders can split across multiple shipments with different
carriers and tracking numbers. This is a known simplification.
V2 extension: add a `shipments` array to support split orders.

## orders.json
Array of order objects. One object per order.

Fields per order:
- order_id (str) — unique identifier e.g. "ORDER-001"
- items (list[str]) — one or more item names in this order
- order_date (str) — ISO date e.g. "2026-09-29"
- expected_date (str) — ISO date e.g. "2026-10-02"
- carrier (str) — e.g. "DHL", "DPD", "Hermes"
- tracking_number (str) — unique, used as key in tracking.json.
  Cancelled orders may have NO entry in tracking.json (e.g. ORDER-013);
  track_package then returns an error dict.
- status (str) — one of: pending | in_transit | delivered | cancelled

## tracking.json
Object keyed by tracking_number. Each value is a list of events.

Fields per event:
- timestamp (str) — ISO datetime e.g. "2026-09-29T14:00:00"
- location (str) — e.g. "Berlin Warehouse", "Leipzig Hub"
- status (str) — one of: label_created | picked_up | in_transit |
                  arrived_at_facility | out_for_delivery | 
                  delivery_attempted | at_depot | delivered
- note (str | null) — optional e.g. "Left at front door"

## Design decisions
- V1: one shipment per order (one carrier, one tracking number)
- items is a list to support multiple items in one shipment
- V2 extension: shipments array for split-carrier orders

## Why different structures
orders.json is a list — queried by scanning (unknown order_id at search time)
tracking.json is a dict — queried by key (tracking_number always known before lookup)