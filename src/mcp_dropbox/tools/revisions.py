"""Revision tools: list_revisions, restore_revision."""

import json
import logging

from dropbox.exceptions import ApiError
from mcp.server.fastmcp import FastMCP

from ..client import DropboxClient

logger = logging.getLogger(__name__)


def register_revision_tools(server: FastMCP, client: DropboxClient) -> None:
    dbx = client.dbx

    @server.tool()
    def list_revisions(path: str, limit: int = 10) -> str:
        """
        List revision history for a file. Free tier retains ~180 days of history.

        Args:
            path: Dropbox path of the file (e.g. /docs/report.pdf).
            limit: Max number of revisions to return (default 10, max 100).
        """
        try:
            result = dbx.files_list_revisions(path, limit=limit)
            revisions = [
                {
                    "rev": entry.rev,
                    "size": entry.size,
                    "modified": str(entry.client_modified),
                    "is_deleted": result.is_deleted,
                }
                for entry in result.entries
            ]
            return json.dumps({
                "status": "success",
                "path": path,
                "count": len(revisions),
                "revisions": revisions,
            })
        except ApiError as e:
            logger.error(f"list_revisions failed: {e}")
            return json.dumps({"status": "error", "error": str(e)})

    @server.tool()
    def restore_revision(path: str, rev: str) -> str:
        """
        Restore a file to a specific revision. Use list_revisions to find rev IDs.

        Args:
            path: Dropbox path of the file.
            rev: Revision ID to restore (from list_revisions).
        """
        try:
            meta = dbx.files_restore(path, rev)
            return json.dumps({
                "status": "success",
                "path": meta.path_display,
                "restored_rev": rev,
                "size": meta.size,
                "modified": str(meta.client_modified),
            })
        except ApiError as e:
            logger.error(f"restore_revision failed: {e}")
            return json.dumps({"status": "error", "error": str(e)})
