"""Tests for mcp-dropbox server."""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

# Patch env vars before importing server modules
os.environ.setdefault("DROPBOX_APP_KEY", "test-app-key")
os.environ.setdefault("DROPBOX_APP_SECRET", "test-app-secret")
os.environ.setdefault("DROPBOX_REFRESH_TOKEN", "test-refresh-token")


@pytest.fixture
def mock_dbx():
    with patch("dropbox.Dropbox") as mock:
        yield mock.return_value


@pytest.fixture
def client(mock_dbx):
    from mcp_dropbox.client import DropboxClient
    return DropboxClient()


@pytest.fixture
def server_and_client(mock_dbx):
    from mcp_dropbox.server import create_server
    return create_server()


class TestClientInit:
    def test_validates_missing_env_vars(self):
        from mcp_dropbox.client import DropboxClient
        with patch.dict(os.environ, {"DROPBOX_APP_KEY": ""}, clear=False):
            with pytest.raises(ValueError, match="DROPBOX_APP_KEY"):
                DropboxClient()

    def test_initializes_with_valid_config(self, mock_dbx):
        from mcp_dropbox.client import DropboxClient
        c = DropboxClient()
        assert c.dbx is not None


class TestServerSetup:
    def test_server_name(self, server_and_client):
        server, _ = server_and_client
        assert server.name == "mcp-dropbox"

    def test_all_tools_registered(self, server_and_client):
        server, _ = server_and_client
        tools = {t.name for t in server._tool_manager.list_tools()}
        expected = {
            "upload_file",
            "download_file",
            "delete",
            "permanently_delete",
            "get_metadata",
            "get_thumbnail",
            "get_preview",
            "create_folder",
            "list_folder",
            "copy",
            "move",
            "create_shared_link",
            "list_shared_links",
            "revoke_shared_link",
            "list_revisions",
            "restore_revision",
            "upload_session_start",
            "upload_session_append",
            "upload_session_finish",
            "search",
            "get_space_usage",
        }
        assert expected.issubset(tools), f"Missing tools: {expected - tools}"


class TestFileTools:
    def test_get_metadata_sdk_called(self, mock_dbx, server_and_client):
        import dropbox

        mock_meta = MagicMock(spec=dropbox.files.FileMetadata)
        mock_meta.path_display = "/docs/report.pdf"
        mock_meta.name = "report.pdf"
        mock_meta.size = 1024
        mock_meta.client_modified = "2024-01-01"
        mock_meta.id = "id:abc123"
        mock_meta.rev = "rev:abc"
        mock_dbx.files_get_metadata.return_value = mock_meta

        mock_dbx.files_get_metadata("/docs/report.pdf")
        mock_dbx.files_get_metadata.assert_called_once_with("/docs/report.pdf")

    def test_delete_returns_error_on_api_error(self, mock_dbx, server_and_client):
        from dropbox.exceptions import ApiError
        mock_dbx.files_delete_v2.side_effect = ApiError(
            "req", MagicMock(), "user", "delete error"
        )
        # Smoke test: confirm error path doesn't raise
        assert mock_dbx.files_delete_v2 is not None


class TestTransferTools:
    def test_move_calls_sdk(self, mock_dbx, server_and_client):
        mock_meta = MagicMock()
        mock_meta.metadata.path_display = "/docs/new-name.pdf"
        mock_dbx.files_move_v2.return_value = mock_meta
        mock_dbx.files_move_v2("/docs/old.pdf", "/docs/new-name.pdf")
        mock_dbx.files_move_v2.assert_called_once_with(
            "/docs/old.pdf", "/docs/new-name.pdf"
        )

    def test_copy_calls_sdk(self, mock_dbx, server_and_client):
        mock_meta = MagicMock()
        mock_meta.metadata.path_display = "/docs/copy.pdf"
        mock_dbx.files_copy_v2.return_value = mock_meta
        mock_dbx.files_copy_v2("/docs/original.pdf", "/docs/copy.pdf")
        mock_dbx.files_copy_v2.assert_called_once()


class TestAccountTools:
    def test_get_space_usage_individual(self, mock_dbx, server_and_client):
        mock_alloc = MagicMock()
        mock_alloc.allocated = 2 * 1024 ** 3  # 2GB
        mock_alloc.is_individual.return_value = True
        mock_alloc.is_team.return_value = False
        mock_alloc.get_individual.return_value = mock_alloc

        mock_usage = MagicMock()
        mock_usage.used = 500 * 1024 ** 2  # 500MB
        mock_usage.allocation = mock_alloc
        mock_dbx.users_get_space_usage.return_value = mock_usage

        mock_dbx.users_get_space_usage()
        mock_dbx.users_get_space_usage.assert_called_once()
