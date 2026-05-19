"""Transfer tools: copy, move (also covers rename)."""

import json
import logging

from dropbox.exceptions import ApiError
from mcp.server.fastmcp import FastMCP

from ..client import DropboxClient

logger = logging.getLogger(__name__)


def register_transfer_tools(server: FastMCP, client: DropboxClient) -> None:
    dbx = client.dbx

    @server.tool()
    def copy(from_path: str, to_path: str, overwrite: bool = False) -> str:
        """
        Copy a file or folder to a new Dropbox path.

        Args:
            from_path: Source path in Dropbox.
            to_path: Destination path in Dropbox.
            overwrite: Replace destination if it already exists. Default False.
        """
        try:
            meta = dbx.files_copy_v2(from_path, to_path, allow_overwrite=overwrite)
            return json.dumps({
                "status": "success",
                "from": from_path,
                "to": meta.metadata.path_display,
            })
        except ApiError as e:
            logger.error(f"copy failed: {e}")
            return json.dumps({"status": "error", "error": str(e)})

    @server.tool()
    def move(from_path: str, to_path: str, overwrite: bool = False) -> str:
        """
        Move or rename a file or folder.
        To rename, keep the parent folder the same and change only the filename.

        Args:
            from_path: Current path in Dropbox.
            to_path: New path in Dropbox.
            overwrite: Replace destination if it already exists. Default False.
        """
        try:
            meta = dbx.files_move_v2(from_path, to_path, allow_overwrite=overwrite)
            return json.dumps({
                "status": "success",
                "from": from_path,
                "to": meta.metadata.path_display,
            })
        except ApiError as e:
            logger.error(f"move failed: {e}")
            return json.dumps({"status": "error", "error": str(e)})
