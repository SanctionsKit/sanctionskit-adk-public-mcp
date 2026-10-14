"""Constrain the actual ADK MCP client to anonymous public tooling."""

import json
import os
from typing import Any

import httpx2
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams

ENDPOINT = "https://www.sanctionskit.com/mcp"
PUBLIC_TOOLS = (
    "search_docs",
    "get_doc",
    "get_api_schema",
    "validate_screening_request",
)


class PublicToolError(RuntimeError):
    """A public tool or its response did not meet the example's contract."""


def require_public_environment() -> None:
    # ADK 2.12 defaults this flag to true and can otherwise attempt Google ADC.
    if os.environ.get("GOOGLE_API_USE_CLIENT_CERTIFICATE", "").lower() != "false":
        raise PublicToolError(
            "Set GOOGLE_API_USE_CLIENT_CERTIFICATE=false before connecting."
        )


def create_public_toolset(
    *, transport: httpx2.AsyncBaseTransport | None = None, audit: list | None = None
) -> McpToolset:
    require_public_environment()
    audit = [] if audit is None else audit

    async def guard(request: httpx2.Request) -> None:
        require_public_environment()
        if str(request.url) != ENDPOINT:
            raise PublicToolError(
                "Only the fixed public SanctionsKit MCP endpoint is permitted."
            )
        if "authorization" in request.headers or "cookie" in request.headers:
            raise PublicToolError(
                "Credential headers are forbidden in this public example."
            )
        if request.method not in {"POST", "GET", "DELETE"}:
            raise PublicToolError("Unexpected HTTP method.")
        entry: dict[str, Any] = {"http_method": request.method}
        if request.method == "POST":
            body = json.loads(request.content)
            method = body.get("method")
            if method not in {
                "initialize",
                "notifications/initialized",
                "tools/list",
                "tools/call",
            }:
                raise PublicToolError("Unexpected MCP operation.")
            entry["mcp_method"] = method
            if method == "tools/call":
                name = body.get("params", {}).get("name")
                if name not in PUBLIC_TOOLS:
                    raise PublicToolError("Account and screening tools are forbidden.")
                entry["tool"] = name
        audit.append(entry)

    def factory(headers=None, timeout=None, auth=None):
        require_public_environment()
        if auth is not None:
            raise PublicToolError("Authentication is forbidden in this public example.")
        return httpx2.AsyncClient(
            headers=headers,
            timeout=timeout,
            trust_env=False,
            follow_redirects=False,
            transport=transport,
            event_hooks={"request": [guard]},
        )

    return McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=ENDPOINT,
            timeout=10,
            sse_read_timeout=20,
            httpx_client_factory=factory,
        ),
        tool_filter=list(PUBLIC_TOOLS),
    )


def response_data(envelope: Any) -> Any:
    # ADK can return a graceful {"error": ...} instead of raising. Never turn
    # that, an MCP error, or an unstructured response into a successful result.
    if not isinstance(envelope, dict) or envelope.get("error") is not None:
        raise PublicToolError("The public MCP call failed.")
    if envelope.get("isError") is not False:
        raise PublicToolError(
            "The public MCP response was an error or lacked an explicit error flag."
        )
    structured = envelope.get("structuredContent")
    if not isinstance(structured, dict) or "data" not in structured:
        raise PublicToolError("The public MCP response lacked structured data.")
    return structured["data"]
