"""Sharing tools: create_shared_link, list_shared_links, revoke_shared_link."""

import json
import logging

import dropbox
from dropbox.exceptions import ApiError
from mcp.server.fastmcp import FastMCP

from ..client import DropboxClient

logger = logging.getLogger(__name__)


def register_sharing_tools(server: FastMCP, client: DropboxClient) -> None:
    dbx = client.dbx

    @server.tool()
    def create_shared_link(path: str, require_password: bool = False) -> str:
        """
        Create a shared link for a file or folder. Anyone with the link can view it.

        Args:
            path: Dropbox path to share (e.g. /docs/report.pdf).
            require_password: Not supported on free tier — included for future use.
        """
        try:
            settings = dropbox.sharing.SharedLinkSettings(
                requested_visibility=dropbox.sharing.RequestedVisibility.public
            )
            result = dbx.sharing_create_shared_link_with_settings(path, settings=settings)
            return json.dumps({
                "status": "success",
                "url": result.url,
                "path": result.path_lower,
                "link_type": type(result).__name__,
            })
        except ApiError as e:
            # If link already exists, return the existing one
            if (
                hasattr(e.error, "is_shared_link_already_exists")
                and e.error.is_shared_link_already_exists()
            ):
                existing = e.error.get_shared_link_already_exists()
                if existing and existing.metadata:
                    return json.dumps({
                        "status": "success",
                        "url": existing.metadata.url,
                        "path": existing.metadata.path_lower,
                        "note": "link already existed",
                    })
            logger.error(f"create_shared_link failed: {e}")
            return json.dumps({"status": "error", "error": str(e)})

    @server.tool()
    def list_shared_links(path: str = "") -> str:
        """
        List shared links, optionally filtered to a specific file or folder.

        Args:
            path: Dropbox path to filter by. Leave empty to list all shared links.
        """
        try:
            kwargs = {}
            if path:
                kwargs["path"] = path
            result = dbx.sharing_list_shared_links(**kwargs)
            links = [
                {
                    "url": link.url,
                    "path": link.path_lower,
                    "link_type": type(link).__name__,
                }
                for link in result.links
            ]
            return json.dumps({
                "status": "success",
                "count": len(links),
                "links": links,
            })
        except ApiError as e:
            logger.error(f"list_shared_links failed: {e}")
            return json.dumps({"status": "error", "error": str(e)})

    @server.tool()
    def revoke_shared_link(url: str) -> str:
        """
        Revoke a shared link so it no longer works.

        Args:
            url: The shared link URL to revoke.
        """
        try:
            dbx.sharing_revoke_shared_link(url)
            return json.dumps({"status": "success", "revoked": url})
        except ApiError as e:
            logger.error(f"revoke_shared_link failed: {e}")
            return json.dumps({"status": "error", "error": str(e)})
