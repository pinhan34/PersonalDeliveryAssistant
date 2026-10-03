# Personal Delivery Assistant

## What this project is
A pure Python AI agent that helps users track their deliveries via natural
language. The user asks "where is my Monday order?" and the agent identifies
the order, retrieves tracking data, interprets the status, and explains what
happened and what to do next.

This is a learning project. The primary goal is understanding the agent loop
and tool calling pattern — not shipping a product.

## Architecture in one line
Streamlit UI → agent loop (loop.py) → 4 tools (tools.py) → fake JSON DB (data/)

## Tech stack
- Python 3.11+
- OpenAI API — gpt-4o-mini, tool calling
- Streamlit — chat UI only
- No frameworks: no LangChain, no LangGraph, no agent libraries

## The 4 tools — contracts
These are fixed. Do not add, remove, or rename tools without being explicitly asked.

| Tool | Input | Returns |
|------|-------|---------|
| identify_order | query: str | list[dict] — may be empty or multiple |
| get_order | order_id: str | dict — single order record |
| track_package | tracking_number: str | dict — events + status_classification |
| get_delivery_estimate | tracking_number: str | dict — date + confidence |

Full contracts in: `.claude/specs/tools.md`

**Claude Code writes:**
- get_order(), track_package(), get_delivery_estimate() in agent/tools.py
- Streamlit UI layout in app.py (not the session_state logic)
- data/orders.json and data/tracking.json

**Pair:**
- identify_order() in agent/tools.py — I write the logic, Claude Code can scaffold

## Critical rules
- Never modify loop.py without being explicitly asked
- Never add tools not listed in the contracts above
- Tools must return dicts — never raw strings, never None
- identify_order must return a list — even for a single match, even for no match
- Never import OpenAI inside tools.py — tools are pure data functions
- Never import Streamlit inside agent/ — UI concerns stay in app.py
- data/ files are read-only at runtime — tools read them, never write them

## Commands
```bash
# Setup
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

# Run
streamlit run app.py

# Test a single tool (once implemented)
python -c "from agent.tools import get_order; print(get_order('ORDER-001'))"
```

## Specs — read before working on that area
- Tools and data contracts → `.claude/specs/tools.md`
- Agent loop behaviour → `.claude/specs/agent-loop.md`
- JSON data structure → `.claude/specs/data-schema.md`

## What is NOT built yet
Everything. This is a blank project.
Start here: `.claude/specs/` → then `data/` → then `agent/` → then `app.py`