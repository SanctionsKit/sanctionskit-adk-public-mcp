"""A deterministic ADK agent: documentation, schema, then structural validation."""

import json
import re
from typing import Any

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.runners import InMemoryRunner
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from pydantic import Field

from .client import PUBLIC_TOOLS, PublicToolError, response_data

INVENTED_REQUEST = {
    "subject": {"name": "Alex Morgan", "entityType": "person"},
    "package": "sandbox@1",
    "retention": "minimal",
}


class PublicDocumentationAgent(BaseAgent):
    """Uses ADK execution/context APIs, without constructing any model client."""

    toolset: McpToolset = Field(exclude=True)

    async def _run_async_impl(self, ctx: InvocationContext):
        tools = {tool.name: tool for tool in await self.toolset.get_tools()}
        if set(tools) != set(PUBLIC_TOOLS):
            raise PublicToolError(
                "The public tool inventory changed; review it before proceeding."
            )
        context = ToolContext(ctx)
        evidence: dict[str, Any] = {}

        async def call(name: str, args: dict) -> Any:
            envelope = await tools[name].run_async(args=args, tool_context=context)
            data = response_data(envelope)
            evidence[name] = envelope
            return data

        results = await call("search_docs", {"query": "screenings", "limit": 1})
        if (
            not isinstance(results, list)
            or not results
            or not isinstance(results[0], dict)
        ):
            raise PublicToolError("No documentation result was returned.")
        # Restrict the response-derived slug; source contents are evidence, not
        # instructions. We do not follow returned URLs or execute their text.
        slug = results[0].get("slug")
        if (
            not isinstance(slug, str)
            or len(slug) > 150
            or re.fullmatch(r"docs/[a-z0-9/-]+", slug) is None
        ):
            raise PublicToolError("Unexpected documentation slug.")
        await call("get_doc", {"slug": slug})
        schema = await call("get_api_schema", {"path": "/screenings", "method": "post"})
        if (
            not isinstance(schema, dict)
            or schema.get("path") != "/screenings"
            or schema.get("method") != "POST"
        ):
            raise PublicToolError("The requested screening schema was not returned.")
        validation = await call(
            "validate_screening_request", {"request": INVENTED_REQUEST}
        )
        if (
            not isinstance(validation, dict)
            or validation.get("scope") != "structure_only"
            or validation.get("coverageChecked") is not False
        ):
            raise PublicToolError(
                "Validation semantics changed; no screening conclusion is permitted."
            )
        if type(validation.get("valid")) is not bool:
            raise PublicToolError("Validation omitted a boolean structural result.")
        report = {
            "kind": "public_documentation_and_structure_validation",
            "invented_request": INVENTED_REQUEST,
            "structurally_valid": validation["valid"],
            "scope": "structure_only",
            "coverage_checked": False,
            "screening_performed": False,
            "meaning": "Request shape only. This is not a screening result, coverage check, or compliance decision.",
            "evidence": evidence,
        }
        yield Event(
            author=self.name,
            content=types.Content(
                role="model", parts=[types.Part(text=json.dumps(report))]
            ),
        )


async def run_example(toolset: McpToolset) -> dict:
    agent = PublicDocumentationAgent(name="public_documentation", toolset=toolset)
    runner = InMemoryRunner(agent=agent, app_name="sanctionskit_public_mcp")
    try:
        events = await runner.run_debug(
            "Inspect the fixed invented request.", quiet=True
        )
        for event in reversed(events):
            if event.author == agent.name and event.content and event.content.parts:
                return json.loads(event.content.parts[0].text)
        raise PublicToolError("The ADK run returned no report.")
    finally:
        try:
            await toolset.close()
        finally:
            await runner.close()
