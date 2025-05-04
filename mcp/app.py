import streamlit as st
import os
import asyncio
import threading
from dotenv import load_dotenv
from client import MCPClient

load_dotenv()

st.set_page_config(page_title="🧠 MCP Chat", layout="wide")
st.title("🧠 MCP + Ollama Chatbot")

# Create background event loop in a thread
if "loop_thread" not in st.session_state:
    loop = asyncio.new_event_loop()
    loop_thread = threading.Thread(target=loop.run_forever, daemon=True)
    loop_thread.start()
    st.session_state.loop = loop
    st.session_state.loop_thread = loop_thread

# Initialize MCP client only once
if "mcp_client" not in st.session_state:
    client = MCPClient()
    st.session_state.mcp_client = client

    # Connect to SSE server asynchronously
    future = asyncio.run_coroutine_threadsafe(
        client.connect_to_sse_server(server_url=os.getenv("MCP_SSE_URL")),
        st.session_state.loop
    )
    try:
        future.result(timeout=10)  # timeout to avoid forever hang
    except Exception as e:
        st.error(f"Failed to connect to MCP server: {e}")

# Async wrapper for processing prompt
def process_query_sync(prompt):
    future = asyncio.run_coroutine_threadsafe(
        st.session_state.mcp_client.process_query(prompt),
        st.session_state.loop
    )
    return future.result()

# Chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages
chat_container = st.container()
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input prompt
prompt = st.chat_input("Ask me something about the weather or math...")
if prompt:
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = process_query_sync(prompt)
            except Exception as e:
                response = f"❌ Error: {e}"
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

# Sidebar controls
with st.sidebar:
    st.header("⚙️ Controls")
    if st.button("🔄 Reset Chat"):
        st.session_state.messages = []
        st.rerun()
    st.markdown("---")
    st.info(
        "**🤖 Try asking things like:**\n\n"
        "**🌤️ Weather**\n"
        "- What’s the weather in Los Angeles?\n"
        "- Are there any alerts in CA?\n\n"
        "**➗ Math**\n"
        "- 2 + 2 * 3\n"
        "- What’s the square root of 144?\n\n"
        "**📊 Dataset Analysis**\n"
        "- Show me the average values of the dataset\n"
        "- How many records are in the file?\n"
        "- What’s the most frequent word in the title?\n"
        "- Do any descriptions mention 'cloud' or 'AI'?\n"
    )

