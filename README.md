# mcp-dropbox

MCP server for Dropbox — full CRUD on files, folders, sharing, revisions, and large file upload sessions.

## Tools

| Tool | Description |
|------|-------------|
| `upload_file` | Upload a local file to Dropbox (up to 150MB) |
| `download_file` | Download a Dropbox file to a local path |
| `delete` | Delete a file or folder (moves to trash) |
| `permanently_delete` | Delete a file or folder, bypassing trash |
| `get_metadata` | Get file/folder info (size, type, modified date) |
| `get_thumbnail` | Get a base64 thumbnail for an image or video |
| `get_preview` | Get a base64 PDF preview for Office documents |
| `create_folder` | Create a new folder |
| `list_folder` | List folder contents (optional recursive) |
| `copy` | Copy a file or folder to a new path |
| `move` | Move or rename a file or folder |
| `create_shared_link` | Generate a shareable URL for a file or folder |
| `list_shared_links` | List existing shared links |
| `revoke_shared_link` | Revoke a shared link |
| `list_revisions` | List revision history for a file |
| `restore_revision` | Restore a file to a prior revision |
| `upload_session_start` | Start a chunked upload session for files >150MB |
| `upload_session_append` | Append the next chunk to an upload session |
| `upload_session_finish` | Finish an upload session and commit the file |
| `search` | Search files and folders by name or content |
| `get_space_usage` | Check used and allocated Dropbox storage |

## Authentication

This server uses OAuth2 with a refresh token. You need three values: an App Key, App Secret, and a Refresh Token.

### Step 1: Create a Dropbox App

1. Go to [dropbox.com/developers/apps](https://www.dropbox.com/developers/apps)
2. Click **Create app**
3. Choose **Scoped access** → **Full Dropbox**
4. Name it anything (e.g. `my-mcp-server`)
5. On the app dashboard, copy your **App key** and **App secret**

### Step 2: Set Permissions

On the app dashboard → **Permissions** tab, enable:

- `files.content.read`
- `files.content.write`
- `files.metadata.read`
- `files.metadata.write`
- `sharing.read`
- `sharing.write`

Click **Submit** after checking them.

### Step 3: Get a Refresh Token

Save the script below as `get_refresh_token.py`, then run it once to authorize the app and get a long-lived refresh token:

```bash
uv run --with dropbox get_refresh_token.py
```

```python
import dropbox
from dropbox import DropboxOAuth2FlowNoRedirect

APP_KEY = "your-app-key"
APP_SECRET = "your-app-secret"

auth_flow = DropboxOAuth2FlowNoRedirect(
    APP_KEY, APP_SECRET, token_access_type="offline"
)

print("Go to this URL and authorize the app:")
print(auth_flow.start())
print()

code = input("Paste the authorization code here: ").strip()
result = auth_flow.finish(code)
print(f"\nDROPBOX_REFRESH_TOKEN={result.refresh_token}")
```

The `token_access_type="offline"` is required — without it you get a short-lived access token that expires in 4 hours instead of a persistent refresh token.

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `DROPBOX_APP_KEY` | Yes | App Key from Dropbox developer console |
| `DROPBOX_APP_SECRET` | Yes | App Secret from Dropbox developer console |
| `DROPBOX_REFRESH_TOKEN` | Yes | OAuth2 refresh token |
| `LOG_LEVEL` | No | Logging level (default: INFO) |

## Installation

```bash
pip install mcp-dropbox
```

Or from source:

```bash
git clone https://github.com/neverprepared/mcp-dropbox
cd mcp-dropbox
pip install -e .
```

## Claude Code Configuration

Add to your `.claude.json` or `~/.claude.json`:

```json
{
  "mcpServers": {
    "dropbox": {
      "command": "mcp-dropbox",
      "env": {
        "DROPBOX_APP_KEY": "your-app-key",
        "DROPBOX_APP_SECRET": "your-app-secret",
        "DROPBOX_REFRESH_TOKEN": "your-refresh-token"
      }
    }
  }
}
```

## License

MIT
