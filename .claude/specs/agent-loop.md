## Loop behaviour

**Max iterations:** 10
- Normal happy path uses 5 iterations maximum
- 10 provides safe headroom for disambiguation scenarios
- Hitting the limit indicates a bug or runaway behaviour

**On hitting max iterations:**
- Return a user-facing error string to the caller
- Do not raise an exception
- Do not return raw tool results
- Error string: "I wasn't able to complete your request. Please try again."

**On unrecognised tool name:**
- Do not crash
- Append an error message to history as a tool result
- Include the list of valid tool names in the error
- Continue the loop — let the LLM self-correct

**Tool execution within one iteration:**
- Execute tool calls sequentially, never in parallel
- If one LLM response contains multiple tool calls, execute in order
- V2 note: use asyncio.gather when a single user query references 
  multiple independent orders — each order becomes a separate chain 
  running concurrently. Not needed while one query = one order.

## History management

**Format — tool results:**
- role must be "tool"
- tool_call_id must match the id from the assistant's tool_call exactly
- content must be a JSON string (json.dumps(result)) — never a raw dict

**System prompt:**
- Injected once at session start in app.py as index 0 of history
- Loop never modifies or re-injects the system prompt

**Persistence:**
- History persists across user turns within one session
- app.py owns history in st.session_state
- Loop receives history, appends to it, returns it — never stores it

**Return value:**
- tuple[str, list] — (final_response_text, updated_history)
- final_response_text: last assistant message content only
- updated_history: full array including all tool calls and results
- Loop never writes to session_state directly — that is app.py's job

**Display vs full history:**
- app.py maintains a separate display list (user + final assistant messages only)
- Tool calls and tool results are never shown to the user
- Full history (including tool internals) is passed to OpenAI only

## Error handling

**Tool raises Python exception:**
- Caught by the loop with try/except around the tool call
- Converted to error dict: {"error": str(e), "tool": tool_name}
- Appended to history as a tool result — loop continues
- LLM reads the error and responds gracefully to the user
- Do not let exceptions bubble up to app.py

**Tool returns wrong shape:**
- Loop validates return type before json.dumps()
- Valid: dict, or list (identify_order returns a list by contract)
- If neither: replace with error dict before appending
- {"error": "Tool X returned Y instead of dict", "tool": tool_name}

**OpenAI API call fails:**
- Caught separately at the LLM call level
- Return immediately: ("I'm having trouble connecting. Please try again.", history)
- Do not attempt to loop again — no LLM means no recovery possible

## Ownership boundaries

**Loop does NOT:**
- Build or modify prompts — prompts.py owns all text
- Implement tool logic — tools.py owns all data functions
- Write to session_state or render UI — app.py owns both
- Own history between turns — receives it, appends to it, returns it

**Loop ONLY:**
- Calls the LLM on each iteration
- Executes tools and appends results to history
- Manages the within-turn history lifecycle
- Returns tuple[str, list] to app.py

## Function signature

def run_agent(user_message: str, history: list) -> tuple[str, list]:

- user_message: raw string from Streamlit, not pre-processed
- history: full conversation array, owned by app.py
- Returns: (final_response_text, updated_history)
- Stateless: stores nothing between calls

## Migration path to LangGraph
loop.py is the only file replaced in a V2 LangGraph migration.
tools.py, tool_schemas.py, prompts.py, and data/ survive unchanged.
Keep loop.py isolated — no tool logic, no prompt logic, no UI logic —
to make this migration a replacement, not a rewrite.