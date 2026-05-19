"""Folder tools: create_folder, list_folder."""

import json
import logging

import dropbox
from dropbox.exceptions import ApiError
from mcp.server.fastmcp import FastMCP

from ..client import DropboxClient

logger = logging.getLogger(__name__)


def register_folder_tools(server: FastMCP, client: DropboxClient) -> None:
    dbx = client.dbx

    @server.tool()
    def create_folder(path: str) -> str:
        """
        Create a new folder in Dropbox.

        Args:
            path: Dropbox path for the new folder (e.g. /projects/2024).
        """
        try:
            meta = dbx.files_create_folder_v2(path)
            return json.dumps({
                "status": "success",
                "path": meta.metadata.path_display,
                "name": meta.metadata.name,
            })
        except ApiError as e:
            logger.error(f"create_folder failed: {e}")
            return json.dumps({"status": "error", "error": str(e)})

    @server.tool()
    def list_folder(path: str = "", recursive: bool = False, limit: int = 100) -> str:
        """
        List the contents of a Dropbox folder.

        Args:
            path: Dropbox folder path. Use empty string or "/" for root.
            recursive: If True, list all nested contents. Default False.
            limit: Max entries to return per page (default 100, max 2000).
        """
        try:
            # Dropbox root must be empty string, not "/"
            if path == "/":
                path = ""

            result = dbx.files_list_folder(path, recursive=recursive, limit=limit)
            entries = []

            while True:
                for entry in result.entries:
                    item = {"name": entry.name, "path": entry.path_display}
                    if isinstance(entry, dropbox.files.FileMetadata):
                        item.update({"type": "file", "size": entry.size})
                    elif isinstance(entry, dropbox.files.FolderMetadata):
                        item["type"] = "folder"
                    elif isinstance(entry, dropbox.files.DeletedMetadata):
                        item["type"] = "deleted"
                    entries.append(item)

                if not result.has_more:
                    break
                result = dbx.files_list_folder_continue(result.cursor)

            return json.dumps({
                "status": "success",
                "path": path or "/",
                "count": len(entries),
                "entries": entries,
            })
        except ApiError as e:
            logger.error(f"list_folder failed: {e}")
            return json.dumps({"status": "error", "error": str(e)})
