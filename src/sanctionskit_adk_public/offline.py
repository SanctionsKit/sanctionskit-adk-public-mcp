"""In-memory MCP protocol fixture used by the real ADK client, without sockets."""

import json
from importlib.resources import files

import httpx2


class OfflineMcpServer:
    def __init__(self):
        self.fixture = json.loads(
            files("sanctionskit_adk_public").joinpath("fixtures.json").read_text()
        )
        self.requests: list[dict] = []

    def handle(self, request: httpx2.Request) -> httpx2.Response:
        if request.method in {"GET", "DELETE"}:
            return httpx2.Response(405)
        body = json.loads(request.content)
        self.requests.append(body)
        method = body.get("method")
        if "id" not in body:
            return httpx2.Response(202)
        if method == "initialize":
            result = {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "offline-example", "version": "1"},
            }
        elif method == "tools/list":
            result = {"tools": self.fixture["tools"]}
        elif method == "tools/call":
            result = self.fixture["responses"][body["params"]["name"]]
        else:
            return httpx2.Response(400)
        return httpx2.Response(
            200, json={"jsonrpc": "2.0", "id": body["id"], "result": result}
        )

    def transport(self) -> httpx2.MockTransport:
        return httpx2.MockTransport(self.handle)
