"""Serve the Python functions in tools/ over MCP Streamable HTTP."""

import importlib
import inspect
import logging
from pathlib import Path

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

LOGGER = logging.getLogger(__name__)


def load_tools(mcp: FastMCP, package_name: str = "tools") -> int:
    """Import top-level modules and expose their locally defined public functions."""
    package = importlib.import_module(package_name)
    # Namespace packages allow the image's tools directory to be completely empty.
    directory = Path(next(iter(package.__path__)))
    count = 0
    for path in sorted(directory.glob("*.py")):
        if path.name.startswith("_"):
            continue
        if not path.stem.isidentifier():
            raise ValueError(f"Tool module must have a valid Python name: {path.name}")
        module_name = f"{package_name}.{path.stem}"
        try:
            module = importlib.import_module(module_name)
            for name, function in inspect.getmembers(module, inspect.isfunction):
                # Keep imported utilities and private helpers out of the MCP catalog.
                if name.startswith("_") or function.__module__ != module_name:
                    continue
                mcp.tool(function)
                LOGGER.info("Loaded tool %s from %s", function.__name__, path.name)
                count += 1
        except Exception as error:
            raise RuntimeError(f"Failed to load tools from {path.name}: {error}") from error
    return count


def create_server() -> FastMCP:
    """Build a server, failing startup if any tool cannot be registered."""
    # Refuse collisions instead of silently replacing an existing tool.
    mcp = FastMCP("xdr-fastmcp", on_duplicate="error")
    count = load_tools(mcp)
    LOGGER.info("Discovered %d tools", count)

    @mcp.custom_route("/health", methods=["GET"])
    async def health(_request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "tools": count})

    return mcp


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    create_server().run(transport="http", host="0.0.0.0", port=8000, path="/mcp")
