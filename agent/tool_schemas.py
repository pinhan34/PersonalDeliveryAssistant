# tool_schemas.py — structure only, no logic

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "identify_order",
            "description": "Searches orders by natural language query. "
                           "Use this FIRST when the user mentions an order "
                           "but has not provided an order_id. "
                           "Do NOT call get_order before calling this first. "
                           "Do NOT call this if the user has already provided "
                           "an exact order_id — use get_order directly instead.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keywords only, not the full user sentence. "
                                       "Item keywords like 'headphones', a weekday like 'Monday', "
                                       "or a date in YYYY-MM-DD format (convert 'September 28' "
                                       "to '2026-09-28'). Relative dates like 'last week' are not supported."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_order",
            "description": "Retrieves an order by its order_id. "
                           "Use this AFTER identify_order has returned an order_id, "
                           "or if the user has already provided an exact order_id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "The unique identifier for the order. "
                                       "Use the exact order_id returned by identify_order, "
                                       "or provided by the user, format ORDER-001."
                    }
                },
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "track_package",
            "description": "Returns where the package is and what happened to it: "
+                           "every scan with location and the carrier's notes "
+                           "(reasons for delays, required actions, deadlines). "
+                           "Call this for ANY question about an order's status or location, "
+                           "together with get_delivery_estimate. "
+                           "Requires tracking_number from get_order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tracking_number": {
                        "type": "string",
                        "description": "The exact tracking_number from the get_order result. "
                                       "Copy it unchanged — the format differs per carrier."
                    }
                },
                "required": ["tracking_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_delivery_estimate",
            "description": "Retrieves the estimated delivery date and the confidence level. "
                           "Call this when the user asks about timing or whether their "
                           "package is late. Requires tracking_number from get_order. "
                           "both only require tracking_number from get_order.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tracking_number": {
                        "type": "string",
                        "description": "The unique identifier for the tracking number. "
                                       "Use the exact tracking_number provided by the user or from previous results."
                    }
                },
                "required": ["tracking_number"]
            }
        }
    }
]