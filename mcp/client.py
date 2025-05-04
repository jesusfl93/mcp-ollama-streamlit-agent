import asyncio
import json
import os
from typing import Optional
from contextlib import AsyncExitStack

import httpx
from mcp import ClientSession
from mcp.client.sse import sse_client
from dotenv import load_dotenv

load_dotenv()


class MCPClient:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.available_tools = []
        self.messages = []

    async def connect_to_sse_server(self, server_url: str):
        print("Connecting to MCP SSE server...")
        self._streams_context = sse_client(url=server_url)
        streams = await self._streams_context.__aenter__()
        print("Streams:", streams)

        self._session_context = ClientSession(*streams)
        self.session: ClientSession = await self._session_context.__aenter__()

        print("Initializing SSE client...")
        await self.session.initialize()
        print("Initialized SSE client")

        await self.get_available_tools()
        await self.get_initial_prompts()

    async def cleanup(self):
        if self._session_context:
            await self._session_context.__aexit__(None, None, None)
        if self._streams_context:
            await self._streams_context.__aexit__(None, None, None)

    async def get_initial_prompts(self):
        prompt = await self.session.get_prompt("get_initial_prompts")
        self.messages = [{"role": msg.role, "content": msg.content.text} for msg in prompt.messages]

    async def get_available_tools(self):
        print("Fetching available server tools...")
        response = await self.session.list_tools()
        print("Connected to MCP server with tools:", [tool.name for tool in response.tools])

        self.available_tools = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                },
                "strict": True,
            }
            for tool in response.tools
        ]

    async def call_ollama(self) -> dict:
        """Call Ollama (qwen3:1.7b) and return full JSON response."""
        timeout = httpx.Timeout(30.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": "qwen3:1.7b",
                    "messages": self.messages,
                    "tools": self.available_tools,
                    "stream": False
                }
            )

            try:
                result = response.json()
            except Exception as e:
                raise Exception(f"Failed to decode JSON: {e} — Raw response: {response.text}")

            #print("Ollama response:", json.dumps(result, indent=2))
            return result

    async def process_query(self, query: str) -> str:
        """Process a user query using Ollama and handle tool calls via MCP."""
        self.messages.append({"role": "user", "content": query})
        response = await self.call_ollama()

        # Tool calling (if supported by the model and triggered)
        if "message" in response and response["message"].get("tool_calls"):
            tool_calls = response["message"]["tool_calls"]
            self.messages.append(response["message"])

            for tool_call in tool_calls:
                tool_name = tool_call["function"]["name"]
                tool_args = tool_call["function"]["arguments"]
                print(f"[Tool call] {tool_name}({tool_args})")

                tool_result = await self.session.call_tool(tool_name, tool_args)
                print(f"[Tool response] {tool_result}")

                if isinstance(tool_result.content, list):
                    text_content = "\n".join(
                        c.text for c in tool_result.content if hasattr(c, "text")
                    )
                else:
                    text_content = str(tool_result.content)

                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.get("id", f"{tool_name}-no-id"),
                    "content": text_content
                })

                return text_content.strip()

        # Basic response (no tools called)
        if "message" in response and "content" in response["message"]:
            self.messages.append(response["message"])
            return response["message"]["content"]

        return "No response from LLM."

        # Basic response
        if "message" in response and "content" in response["message"]:
            self.messages.append(response["message"])
            return response["message"]["content"]

        return "No response from LLM."

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                print("\n" + "-" * 100)
                query = input("\nQuery: ").strip()

                if query.lower() == 'quit':
                    break

                if query:
                    reply = await self.process_query(query)
                    print("\nAssistant:", reply)

            except Exception as e:
                import traceback
                print("\nError:")
                traceback.print_exc()


async def main():
    client = MCPClient()
    try:
        await client.connect_to_sse_server(server_url=os.getenv("MCP_SSE_URL"))
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
