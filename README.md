
# 🧠 MCP + Ollama Streamlit Chatbot

This repository contains a fully functional multi-agent chatbot powered by the **Model Context Protocol (MCP)**, **Ollama** with the `qwen3:1.7b` model, and a **Streamlit-based frontend**. The chatbot supports tool calling and integrates domain-specific utilities like weather APIs, math evaluation, and CSV dataset analysis.

---

## 📁 Project Structure

```
.
├── app.py             # Streamlit frontend interface
├── client.py          # Async MCP client with Ollama integration and tool handling
├── server.py          # MCP-compatible server with weather, math, and dataset tools
├── data/
│   └── dataset.csv    # Sample CSV file for dataset analysis
├── .env               # Environment variables (MCP_SSE_URL, etc.)
```

---

## 🧰 Features & Tools

The assistant supports the following built-in tools via MCP server:

- 🌤️ **Weather Tools** – Fetch alerts and forecasts using the [National Weather Service API](https://www.weather.gov/documentation/services-web-api)
- ➗ **Math Evaluator** – Safe evaluation of arithmetic expressions
- 📊 **Dataset Inspector** – Summary statistics, shape, and NLP-powered queries on a local `dataset.csv` file

---



```mermaid
flowchart TD
    subgraph "🧠 Streamlit UI"
        A1[User Prompt]
        A2[Display Chat History]
        A3[Streamlit App (app.py)]
    end

    subgraph "📡 MCP Client (client.py)"
        B1[Connect to SSE Server]
        B2[Process Query]
        B3[Call Ollama API]
        B4[Handle Tool Calls]
    end

    subgraph "⚙️ MCP Server (server.py)"
        C1[Tool: Weather Alerts]
        C2[Tool: Forecast]
        C3[Tool: Math Evaluation]
        C4[Tool: Dataset Analysis]
        C5[Tool: Dataset Query]
    end

    subgraph "🧠 Ollama"
        D1[qwen3:1.7b Model]
    end

    A1 --> A3
    A3 --> B2
    A2 --> A3
    B2 --> B3
    B3 --> D1
    D1 --> B4
    B4 -->|Tool Call| C1
    B4 -->|Tool Call| C2
    B4 -->|Tool Call| C3
    B4 -->|Tool Call| C4
    B4 -->|Tool Call| C5
    C1 --> B2
    C2 --> B2
    C3 --> B2
    C4 --> B2
    C5 --> B2
```




## 🔧 Requirements

Ensure you have the following installed:

- Python 3.9+
- Ollama with the `qwen3:1.7b` model available locally
- MCP library (see installation below)
- [Streamlit](https://streamlit.io)
- [Uvicorn](https://www.uvicorn.org/) for ASGI server
- A `.env` file with MCP server URL defined:
  ```env
  MCP_SSE_URL=http://localhost:8080/sse
  ```

### Python Packages

You can install all required packages via:

```bash
pip install -r requirements.txt
```

If you don't have a `requirements.txt`, use:

```bash
pip install streamlit uvicorn httpx python-dotenv pandas scikit-learn mcp
```

---

## ▶️ How to Run

### 1. Launch the MCP Server (Tool Provider)

Run the server to expose SSE-compatible endpoints:

```bash
python server.py --host 0.0.0.0 --port 8080
```

This will start a FastAPI-compatible MCP server exposing tools on:
```
http://localhost:8080/sse
```

### 2. Start the Streamlit Frontend

In another terminal:

```bash
streamlit run app.py
```

This will open the chat interface in your browser at:
```
http://localhost:8501
```

---

## 📦 Ollama Model Setup

Install and run Ollama:

```bash
ollama pull qwen3:1.7b
ollama run qwen3:1.7b
```

Ensure the model is loaded and responding at:
```
http://localhost:11434/api/chat
```

---

## 🧪 Supported Use Cases

Here are some queries you can try:

### Weather
- *What’s the weather in San Francisco?*
- *Are there any alerts in NY?*

### Math
- *What is 2 + 3 * 4?*
- *Calculate the square root of 81*

### Dataset Analysis
- *What are the columns in the dataset?*
- *How many records are in the file?*
- *Do any descriptions mention "cloud" or "AI"?*

---

## 🧼 Resetting State

You can reset the chat history using the sidebar button in the Streamlit UI.

---

## 📁 Notes

- Make sure `data/dataset.csv` exists if using dataset tools.
- Ensure `MCP_SSE_URL` in `.env` matches your server setup.
- This system uses `asyncio.run_coroutine_threadsafe()` to allow asynchronous tool execution within Streamlit's synchronous model.
