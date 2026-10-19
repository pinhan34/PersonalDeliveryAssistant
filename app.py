import streamlit as st

from agent.loop import run_agent
from agent.prompts import SYSTEM_PROMPT

EXAMPLE_QUESTIONS = [
    "Where is my Monday order?",
    "My office chair has not arrived yet",
    "When will my running shoes arrive?",
    "What happened to my air fryer?",
    "What's the status of ORDER-004?",
]

st.set_page_config(page_title="Delivery Assistant", page_icon="📦")

# --- Session state ---
if "history" not in st.session_state:
    st.session_state.history = [{"role": "system", "content": SYSTEM_PROMPT}]
if "display" not in st.session_state:
    st.session_state.display = []

# --- Sidebar ---
clicked_example = None

with st.sidebar:
    st.header("📦 Delivery Assistant")
    st.caption("Ask in plain language — I'll find the order, check tracking "
               "and tell you what to do next.")

    st.subheader("Try asking")
    for question in EXAMPLE_QUESTIONS:
        if st.button(question, width="stretch"):
            clicked_example = question

    st.divider()
    show_steps = st.toggle("🔧 Show agent steps", value=False)
    reset_clicked = st.button("🔄 New conversation", type="primary", width="stretch")

# --- Reset ---
if reset_clicked:
    st.session_state.history = [{"role": "system", "content": SYSTEM_PROMPT}]
    st.session_state.display = []

# --- Chat ---
st.title("Where's my parcel?")

if not st.session_state.display:
    st.info("Ask about any of your orders, or pick an example from the sidebar.")

for msg in st.session_state.display:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

typed = st.chat_input("Ask about a delivery…")
prompt = typed or clicked_example

if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Checking your orders…"):
            answer, st.session_state.history = run_agent(prompt, st.session_state.history)
            st.session_state.display.append({"role": "user", "content": prompt})
            st.session_state.display.append({"role": "assistant", "content": answer})

        st.markdown(answer)
