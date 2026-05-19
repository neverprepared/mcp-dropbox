"""MCP server setup and tool registration."""

import logging

from mcp.server.fastmcp import FastMCP

from .client import DropboxClient
from .tools.account import register_account_tools
from .tools.files import register_file_tools
from .tools.folders import register_folder_tools
from .tools.revisions import register_revision_tools
from .tools.search import register_search_tools
from .tools.sharing import register_sharing_tools
from .tools.transfer import register_transfer_tools
from .tools.upload_session import register_upload_session_tools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_server() -> tuple[FastMCP, DropboxClient]:
    server = FastMCP("mcp-dropbox")
    client = DropboxClient()

    register_file_tools(server, client)
    register_folder_tools(server, client)
    register_transfer_tools(server, client)
    register_sharing_tools(server, client)
    register_revision_tools(server, client)
    register_upload_session_tools(server, client)
    register_search_tools(server, client)
    register_account_tools(server, client)

    logger.info("mcp-dropbox server ready with %d tool modules", 8)
    return server, client


def run():
    server, _client = create_server()
    server.run(transport="stdio")
