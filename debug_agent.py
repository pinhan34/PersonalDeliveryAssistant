from agent.loop import run_agent
from agent.prompts import SYSTEM_PROMPT

history = [{"role": "system", "content": SYSTEM_PROMPT}]

answer, history = run_agent("My office chair has not arrived yet!", history)
print(answer)
