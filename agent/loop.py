import json

from dotenv import load_dotenv
from openai import OpenAI, OpenAIError

from agent import tools
from agent.tool_schemas import TOOL_SCHEMAS

load_dotenv()          # reads OPENAI_API_KEY from .env
client = OpenAI()

MAX_ITERATIONS = 10

TOOLS = {
    "identify_order": tools.identify_order,
    "get_order": tools.get_order,
    "track_package": tools.track_package,
    "get_delivery_estimate": tools.get_delivery_estimate,
}


def run_agent(user_message: str, history: list) -> tuple[str, list]:
    """
    Runs one user turn: asks the model, executes the tools it requests,
    and repeats until the model answers in plain text.
    Returns (final_response_text, updated_history).
    """
    history.append({"role": "user", "content": user_message})

    for _ in range(MAX_ITERATIONS):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=history,
                tools=TOOL_SCHEMAS,
                temperature=0.2,
            )
        except OpenAIError:
            return "I'm having trouble connecting. Please try again.", history

        message = response.choices[0].message
        # store as a plain dict so history stays JSON-friendly for session_state
        history.append(message.model_dump(exclude_none=True))

        if not message.tool_calls:
            return message.content, history

        for tool_call in message.tool_calls:
            result = _execute_tool(tool_call.function.name, tool_call.function.arguments)
            history.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result),
            })

    return "I wasn't able to complete your request. Please try again.", history


def _execute_tool(tool_name: str, raw_arguments: str) -> dict | list:
    """
    Runs one tool and always returns something the model can read —
    errors become {"error": ...} instead of crashing the loop.
    """
    if tool_name not in TOOLS:
        return {"error": f"Unknown tool '{tool_name}'", "valid_tools": list(TOOLS)}

    try:
        args = json.loads(raw_arguments)        # '{"query": "Monday"}' -> {"query": "Monday"}
        result = TOOLS[tool_name](**args)       # get_order(**{"order_id": "X"}) -> get_order(order_id="X")
    except Exception as e:
        return {"error": str(e), "tool": tool_name}

    # identify_order returns a list by contract; every other tool returns a dict
    if not isinstance(result, (dict, list)):
        return {"error": f"Tool {tool_name} returned {type(result).__name__} instead of dict",
                "tool": tool_name}
    return result
