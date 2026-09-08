# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Overview

`mcp-dropbox` is a Model Context Protocol (MCP) server exposing the Dropbox API as
MCP tools. It is a Python package (`src/mcp_dropbox`) built with hatchling, runs
over **stdio** transport, and authenticates to Dropbox with OAuth2 refresh-token
credentials supplied via environment variables.

- Python: `>=3.11`
- Runtime deps: `mcp>=1.0.0`, `dropbox>=12.0.0`
- Console script: `mcp-dropbox` → `mcp_dropbox.server:run`

## Architecture

```
src/mcp_dropbox/
  __main__.py        # `python -m mcp_dropbox` -> calls server.run()
  server.py          # create_server() builds FastMCP("mcp-dropbox") + DropboxClient,
                     # then calls each register_*_tools(server, client); run() serves stdio
  client.py          # DropboxClient: validates env vars, wraps dropbox.Dropbox,
                     # exposes .dbx and .check_auth()
  tools/             # one module per capability area, each exporting register_*_tools
    files.py         upload_file, download_file, delete, permanently_delete,
                     get_metadata, get_thumbnail, get_preview
    folders.py       create_folder, list_folder
    transfer.py      copy, move
    sharing.py       create_shared_link, list_shared_links, revoke_shared_link
    revisions.py     list_revisions, restore_revision
    upload_session.py upload_session_start, upload_session_append, upload_session_finish
    search.py        search
    account.py       get_space_usage
tests/test_server.py # pytest suite; mocks dropbox.Dropbox, no network
```

**Registration flow**: `create_server()` is the single wiring point. Adding a new
tool module means creating `tools/<area>.py` with a `register_<area>_tools(server,
client)` function and calling it from `create_server()`. There are currently
**8 tool modules exposing 21 tools**. No MCP *resources* or *prompts* are exposed —
tools only.

## Environment Variables

| Variable | Required | Notes |
|---|---|---|
| `DROPBOX_APP_KEY` | Yes | Validated at `DropboxClient.__init__`; missing → `ValueError` |
| `DROPBOX_APP_SECRET` | Yes | Same |
| `DROPBOX_REFRESH_TOKEN` | Yes | Same; `token_access_type="offline"` required when minting it |

All three are read in `client.py::_validate_config`. The client is constructed
eagerly in `create_server()`, so the server fails fast at startup if any is unset.

## Key Commands

```bash
# Install (editable, from source)
uv sync                      # or: pip install -e .

# Run the server (stdio; requires the three DROPBOX_* env vars)
mcp-dropbox
python -m mcp_dropbox

# Test — pytest/pytest-asyncio are NOT declared deps, pass them explicitly
uv run --with pytest --with pytest-asyncio pytest -q

# Build
uv build
```

There is **no linter configured** (no ruff/flake8/black config, no `make lint`) and
**no CI workflow** (`.github/` does not exist). Verification is the pytest suite.

## Conventions

- **Every tool returns a JSON string**, never a Python object:
  `json.dumps({"status": "success", ...})` on success,
  `json.dumps({"status": "error", "error": str(e)})` on failure.
- **Tools are sync `def`**, not `async def`, and are registered with `@server.tool()`
  inside the module's `register_*_tools` closure. The closure captures
  `dbx = client.dbx`.
- **Errors are caught, not raised.** Wrap Dropbox SDK calls in
  `try/except ApiError`, `logger.error(...)`, and return the error JSON. Do not let
  an exception escape a tool.
- **Docstrings are the tool schema.** FastMCP surfaces the docstring to the model —
  write a one-line summary plus an `Args:` block describing every parameter,
  including path format examples (e.g. `/docs/report.pdf`).
- Dropbox paths use a leading `/`; the account root is the empty string `""`.
- Tests mock `dropbox.Dropbox` via `patch` and set the `DROPBOX_*` env vars at module
  import time. Never write a test that hits the live Dropbox API.

## Gotchas

- `upload_file` uses the single-shot `files_upload` API, capped at 150MB. Files above
  that require the `upload_session_*` trio.
- `upload_session_finish` re-opens `local_path` to read the final chunk, so the local
  file must still exist and be unchanged when it is called.
- `pyproject.toml` sets `asyncio_mode = "auto"`, which requires `pytest-asyncio` —
  it is not declared anywhere, so it must be installed ad hoc (see Key Commands).
- CLAUDE.md is matched by a global gitignore; commit it with `git add -f CLAUDE.md`.
