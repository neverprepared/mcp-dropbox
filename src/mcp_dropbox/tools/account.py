"""Account tools: get_space_usage."""

import json
import logging

from dropbox.exceptions import ApiError
from mcp.server.fastmcp import FastMCP

from ..client import DropboxClient

logger = logging.getLogger(__name__)


def register_account_tools(server: FastMCP, client: DropboxClient) -> None:
    dbx = client.dbx

    @server.tool()
    def get_space_usage() -> str:
        """Get Dropbox storage usage — used bytes and total allocated."""
        try:
            usage = dbx.users_get_space_usage()
            used = usage.used
            allocation = usage.allocation

            result: dict = {"status": "success", "used_bytes": used}

            if allocation.is_individual():
                alloc = allocation.get_individual()
                result["allocated_bytes"] = alloc.allocated
                result["used_percent"] = round((used / alloc.allocated) * 100, 2)
            elif allocation.is_team():
                alloc = allocation.get_team()
                result["team_used_bytes"] = alloc.used
                result["team_allocated_bytes"] = alloc.allocated

            return json.dumps(result)
        except ApiError as e:
            logger.error(f"get_space_usage failed: {e}")
            return json.dumps({"status": "error", "error": str(e)})
