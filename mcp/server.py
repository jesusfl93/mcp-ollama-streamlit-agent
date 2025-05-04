from typing import Any
import httpx
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from mcp.server.sse import SseServerTransport
from starlette.requests import Request
from starlette.routing import Mount, Route
from mcp.server import Server
from mcp.server.fastmcp.prompts import base
import pandas as pd
import re
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS


import uvicorn

# Initialize FastMCP server for Weather tools (SSE)
mcp = FastMCP("weather")

# Constants
NWS_API_BASE = "https://api.weather.gov"
USER_AGENT = "weather-app/1.0"


async def make_nws_request(url: str) -> dict[str, Any] | None:
    """Make a request to the NWS API with proper error handling."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None


def format_alert(feature: dict) -> str:
    """Format an alert feature into a readable string."""
    props = feature["properties"]
    return f"""
Event: {props.get('event', 'Unknown')}
Area: {props.get('areaDesc', 'Unknown')}
Severity: {props.get('severity', 'Unknown')}
Description: {props.get('description', 'No description available')}
Instructions: {props.get('instruction', 'No specific instructions provided')}
"""


@mcp.tool()
async def get_alerts(state: str) -> str:
    """Get weather alerts for a US state.

    Args:
        state: Two-letter US state code (e.g. CA, NY)
    """
    print(state)
    url = f"{NWS_API_BASE}/alerts/active/area/{state}"
    data = await make_nws_request(url)

    if not data or "features" not in data:
        return "Unable to fetch alerts or no alerts found."

    if not data["features"]:
        return "No active alerts for this state."

    alerts = [format_alert(feature) for feature in data["features"]]
    return "\n---\n".join(alerts)


@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """Get weather forecast for a location.

    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location
    """
    print('Printing: ',latitude,'--',longitude)
    # First get the forecast grid endpoint
    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"
    points_data = await make_nws_request(points_url)

    if not points_data:
        return "Unable to fetch forecast data for this location."

    # Get the forecast URL from the points response
    forecast_url = points_data["properties"]["forecast"]
    forecast_data = await make_nws_request(forecast_url)

    if not forecast_data:
        return "Unable to fetch detailed forecast."

    # Format the periods into a readable forecast
    periods = forecast_data["properties"]["periods"]
    forecasts = []
    for period in periods[:5]:  # Only show next 5 periods
        forecast = f"""
{period['name']}:
Temperature: {period['temperature']}°{period['temperatureUnit']}
Wind: {period['windSpeed']} {period['windDirection']}
Forecast: {period['detailedForecast']}
"""
        forecasts.append(forecast)

    return "\n---\n".join(forecasts)

@mcp.tool()
def calculate_expression(expression: str) -> str:
    """
    Safely evaluate a simple math expression (e.g., "2 + 2 * 3").

    Args:
        expression: A math expression in string format

    Returns:
        Result of the expression as a string
    """
    import ast
    import operator as op

    allowed_operators = {
        ast.Add: op.add,
        ast.Sub: op.sub,
        ast.Mult: op.mul,
        ast.Div: op.truediv,
        ast.Pow: op.pow,
        ast.USub: op.neg,
    }

    def eval_node(node):
        if isinstance(node, ast.Num):
            return node.n
        elif isinstance(node, ast.BinOp):
            return allowed_operators[type(node.op)](eval_node(node.left), eval_node(node.right))
        elif isinstance(node, ast.UnaryOp):
            return allowed_operators[type(node.op)](eval_node(node.operand))
        else:
            raise TypeError(f"Unsupported type: {type(node)}")

    try:
        parsed = ast.parse(expression, mode='eval')
        result = eval_node(parsed.body)
        return str(result)
    except Exception as e:
        return f"Error: {str(e)}"
    

@mcp.tool()
def analyze_dataset(action: str = "summary") -> str:
    """
    Analyze a CSV dataset and return insights.

    Args:
        action: Type of analysis: "shape", "summary", or "columns"

    Returns:
        Text summary of the dataset
    """
    try:
        df = pd.read_csv("data/dataset.csv")

        print(action)

        if action == "shape":
            return f"The dataset has {df.shape[0]} rows and {df.shape[1]} columns."

        elif action == "columns":
            return f"The dataset contains the following columns:\n- " + "\n- ".join(df.columns)

        elif action == "summary":
            return str(df.describe(include='all').to_string())

        else:
            return "Unsupported action. Use 'shape', 'columns', or 'summary'."

    except Exception as e:
        return f"Error analyzing dataset: {str(e)}"

@mcp.tool()
def query_dataset(question: str) -> str:
    """
    Answer natural language questions about the dataset.csv file using the 'title' and 'description' columns.

    Args:
        question: Natural language question from the user

    Returns:
        String answer based on the dataset
    """

    try:
        df = pd.read_csv("data/dataset.csv")
        q = question.lower()

        # Quick responses
        if "how many" in q and "titles" in q:
            return f"There are {df['title'].nunique()} unique titles in the dataset."
        if "how many" in q and ("rows" in q or "records" in q):
            return f"The dataset contains {len(df)} rows."

        # Extract candidate keywords from question
        words = re.findall(r'\b\w+\b', q)
        tokens = [w for w in words if w not in ENGLISH_STOP_WORDS and len(w) > 2]

        if not tokens:
            return "I couldn't find any useful keywords to search."

        # Match keywords in title and description
        matches = []
        for token in tokens:
            title_count = df['title'].str.contains(token, case=False, na=False).sum()
            desc_count = df['description'].str.contains(token, case=False, na=False).sum()
            if title_count + desc_count > 0:
                matches.append(f"'{token}' found in {title_count} titles and {desc_count} descriptions")

        if matches:
            return "; ".join(matches)
        else:
            return "No matches found for your question keywords."

    except Exception as e:
        return f"Error while processing your question: {str(e)}"


@mcp.prompt()
def get_initial_prompts() -> list[base.Message]:
    return [
        base.UserMessage("""You are a helpful assistant that can help with weather-related questions.
                            For math expressions like '2 + 3 * 4', use the `calculate_expression` tool.
                            Reply general questions using your knowledge like thins about animals or general.

                         """),
    ]

def create_starlette_app(mcp_server: Server, *, debug: bool = False) -> Starlette:
    """Create a Starlette application that can server the provied mcp server with SSE."""
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request) -> None:
        async with sse.connect_sse(
                request.scope,
                request.receive,
                request._send,  # noqa: SLF001
        ) as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )

    return Starlette(
        debug=debug,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ],
    )


if __name__ == "__main__":
    mcp_server = mcp._mcp_server  # noqa: WPS437

    import argparse
    
    parser = argparse.ArgumentParser(description='Run MCP SSE-based server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to listen on')
    args = parser.parse_args()

    # Bind SSE request handling to MCP server
    starlette_app = create_starlette_app(mcp_server, debug=True)

    uvicorn.run(starlette_app, host=args.host, port=args.port)