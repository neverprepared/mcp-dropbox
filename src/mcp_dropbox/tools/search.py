"""Search tools: search files and folders by name or content."""

import json
import logging

import dropbox
from dropbox.exceptions import ApiError
from mcp.server.fastmcp import FastMCP

from ..client import DropboxClient

logger = logging.getLogger(__name__)


def register_search_tools(server: FastMCP, client: DropboxClient) -> None:
    dbx = client.dbx

    @server.tool()
    def search(query: str, path: str = "", max_results: int = 20) -> str:
        """
        Search for files and folders in Dropbox by name or content.

        Args:
            query: Search term (filename or content keyword).
            path: Limit search to this Dropbox folder. Leave empty to search everywhere.
            max_results: Maximum results to return (default 20, max 1000).
        """
        try:
            options = dropbox.files.SearchOptions(
                path=path if path else None,
                max_results=max_results,
            )
            result = dbx.files_search_v2(query, options=options)
            matches = []
            for match in result.matches:
                meta = match.metadata.get_metadata()
                item = {"name": meta.name, "path": meta.path_display}
                if isinstance(meta, dropbox.files.FileMetadata):
                    item.update({"type": "file", "size": meta.size})
                elif isinstance(meta, dropbox.files.FolderMetadata):
                    item["type"] = "folder"
                matches.append(item)

            return json.dumps({
                "status": "success",
                "query": query,
                "count": len(matches),
                "has_more": result.has_more,
                "matches": matches,
            })
        except ApiError as e:
            logger.error(f"search failed: {e}")
            return json.dumps({"status": "error", "error": str(e)})
