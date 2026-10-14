"""Offline by default. Live mode calls only four anonymous public tools."""

import argparse
import asyncio
import json
import os


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live-public",
        action="store_true",
        help="Use the fixed public MCP endpoint instead of offline fixtures.",
    )
    args = parser.parse_args()
    # Set before ADK imports/initialization; never let the public example attempt
    # ambient Google credential discovery or export OpenTelemetry traces.
    os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"
    os.environ["OTEL_SDK_DISABLED"] = "true"
    from .client import create_public_toolset
    from .offline import OfflineMcpServer
    from .workflow import run_example

    async def run():
        audit: list = []
        server = None if args.live_public else OfflineMcpServer()
        toolset = create_public_toolset(
            transport=server.transport() if server else None, audit=audit
        )
        report = await run_example(toolset)
        report["execution"] = {
            "mode": "live_public" if args.live_public else "offline_fixture",
            "model_calls": 0,
            "account_tools_called": 0,
            "requests": audit,
        }
        print(json.dumps(report, indent=2))

    asyncio.run(run())


if __name__ == "__main__":
    main()
