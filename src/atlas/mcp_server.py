"""Optional stdio MCP server: pip install -e '.[mcp]' && python -m atlas.mcp_server."""
import json

from atlas.store import Store
from atlas.tools import safe_calculate

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:
    raise SystemExit("Install the optional MCP dependency: pip install -e '.[mcp]'") from exc

mcp = FastMCP("ATLAS Knowledge Tools")


@mcp.tool()
def search_documents(query: str) -> str:
    """Return local document snippets with source IDs for grounded research."""
    return json.dumps(Store().search(query, limit=5))


@mcp.tool()
def calculator(expression: str) -> str:
    """Evaluate numeric arithmetic using a safe expression parser."""
    try:
        return str(safe_calculate(expression))
    except ValueError as exc:
        return f"Error: {exc}"


@mcp.tool()
def list_documents() -> str:
    """List the locally indexed knowledge documents."""
    return json.dumps(Store().list_documents())


if __name__ == "__main__":
    mcp.run(transport="stdio")
