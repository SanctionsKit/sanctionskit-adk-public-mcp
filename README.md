# SanctionsKit public MCP with Google ADK

A small, model-free ADK agent searches API documentation, reads a document, fetches the `POST /screenings` schema, and validates the **shape** of one invented request. It demonstrates `BaseAgent`, `InMemoryRunner`, `ToolContext`, and `McpToolset` using the real ADK implementation.

This is a development example for a proposed Google ADK community recipe. It is not an accepted upstream recipe or a hosted deployment. The official route is the [new recipe proposal](https://github.com/google/adk-recipes/issues/new?template=propose-a-new-recipe.md). Approval is required before adding a new recipe to upstream `contrib/` and opening a PR. The [checklist](https://github.com/google/adk-recipes/blob/main/docs/recipe-checklist.md) also requires a Google CLA, real maintainer ownership, and a deployable container; those contribution gates remain open.

## Setup

Use Python 3.11 or later. Verification used Python 3.12.14, `google-adk==2.12.0`, `mcp==2.3.0`, and `httpx2==2.13.1`. Other runtime versions have not been verified.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install '.[test]'
```

Alternatively, `uv sync --extra test` installs the recorded lock file. No model key, Google account, or SanctionsKit account is needed. `.env.example` documents the two environment controls; the CLI sets them explicitly and does not load a credential file.

## Run

Offline is the default. It uses the actual ADK runner and MCP protocol client with an in-memory HTTP transport. The response fixtures are synthetic, are labeled as such, and make no current coverage claims.

```sh
sanctionskit-adk-public
```

To inspect the current public documentation and validate the invented request against the anonymous public MCP endpoint:

```sh
sanctionskit-adk-public --live-public
```

The agent does not interpret arbitrary user prompts. Its workflow and invented request are fixed. It calls only:

1. `search_docs` for screening documentation.
2. `get_doc` for the returned documentation slug.
3. `get_api_schema` for `POST /screenings`.
4. `validate_screening_request` for the fixed invented request.

The printed report preserves the tool envelopes and explicitly records `scope: structure_only`, `coverage_checked: false`, and `screening_performed: false`. `structurally_valid: false` remains a failed structural check. A successful shape check does not establish available packages, sanctions coverage, a match/no-match result, or a compliance decision.

`sandbox@1` is only a field in the invented request. This example does **not** run the synthetic sandbox. Running that screening tool requires a connected sandbox account; paid production screening is a separate product workflow. No screening allowance is consumed by these four public tools. See [SanctionsKit MCP documentation](https://www.sanctionskit.com/resources/mcp) for current tool boundaries.

## Safety and failure behavior

The tool filter and an independent HTTP request guard permit only the four named public tools at `https://www.sanctionskit.com/mcp`. The transport rejects authentication, Authorization/Cookie headers, unexpected MCP operations, and other destinations. It disables redirects and environment proxy configuration. It does not follow returned documentation URLs or execute source text. Errors and malformed results stop the workflow; no fallback produces a screening conclusion.

The CLI sets `GOOGLE_API_USE_CLIENT_CERTIFICATE=false` before constructing ADK objects. In ADK 2.12.0, leaving that setting at its default can trigger an ambient Google credential lookup for mTLS even for a public endpoint. The Python factory refuses to connect unless this flag is explicitly false. `OTEL_SDK_DISABLED=true` disables trace export for the CLI. The agent constructs no model client.

Both the toolset and runner close on success or failure. ADK currently emits experimental authentication and MCP-tool warnings even though this example supplies no authentication. They are not hidden.

## Tests

```sh
python -m pytest -q
```

The offline tests exercise the installed ADK runner and actual MCP protocol transport, with socket connections and Google credential discovery patched to fail. They cover public-tool filtering against a nine-tool inventory, account-call blocking even if the filter is bypassed, errors, missing tools, invalid validation, response-semantic changes, and cleanup. The local verification also exercised these four anonymous tools against the public endpoint with credential discovery blocked. This does not establish account-tool or production compatibility.

The package contains original company code and synthetic fixtures under the MIT license. Private research records are not included. Support: support@sanctionskit.com. Source and issue status should be checked before treating this development example as an upstream integration.
