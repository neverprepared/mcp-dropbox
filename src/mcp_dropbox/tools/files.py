"""File CRUD tools: upload, download, delete, metadata, thumbnail, preview, permanently_delete."""

import base64
import json
import logging
import os

import dropbox
from dropbox.exceptions import ApiError
from mcp.server.fastmcp import FastMCP

from ..client import DropboxClient

logger = logging.getLogger(__name__)

CHUNK_SIZE = 4 * 1024 * 1024  # 4MB read chunks for download


def register_file_tools(server: FastMCP, client: DropboxClient) -> None:
    dbx = client.dbx

    @server.tool()
    def upload_file(local_path: str, dropbox_path: str, overwrite: bool = True) -> str:
        """
        Upload a local file to Dropbox.

        Args:
            local_path: Absolute path to the local file to upload.
            dropbox_path: Destination path in Dropbox (e.g. /docs/report.pdf).
            overwrite: Replace existing file if True (default). Set False to fail if file exists.
        """
        try:
            mode = (
                dropbox.files.WriteMode.overwrite
                if overwrite
                else dropbox.files.WriteMode.add
            )
            file_size = os.path.getsize(local_path)

            with open(local_path, "rb") as f:
                if file_size <= 150 * 1024 * 1024:
                    meta = dbx.files_upload(f.read(), dropbox_path, mode=mode)
                else:
                    # Large files use upload sessions (handled separately)
                    return json.dumps({
                        "status": "error",
                        "error": "File exceeds 150MB. Use upload_session_start/append/finish for large files.",
                    })

            return json.dumps({
                "status": "success",
                "path": meta.path_display,
                "size": meta.size,
                "id": meta.id,
            })
        except ApiError as e:
            logger.error(f"upload_file failed: {e}")
            return json.dumps({"status": "error", "error": str(e)})
        except FileNotFoundError:
            return json.dumps({"status": "error", "error": f"Local file not found: {local_path}"})

    @server.tool()
    def download_file(dropbox_path: str, local_path: str) -> str:
        """
        Download a file from Dropbox to a local path.

        Args:
            dropbox_path: Path in Dropbox (e.g. /docs/report.pdf).
            local_path: Absolute local path to save the file to.
        """
        try:
            meta, response = dbx.files_download(dropbox_path)
            os.makedirs(os.path.dirname(os.path.abspath(local_path)), exist_ok=True)
            with open(local_path, "wb") as f:
                f.write(response.content)
            return json.dumps({
                "status": "success",
                "path": meta.path_display,
                "size": meta.size,
                "saved_to": local_path,
            })
        except ApiError as e:
            logger.error(f"download_file failed: {e}")
            return json.dumps({"status": "error", "error": str(e)})

    @server.tool()
    def delete(path: str) -> str:
        """
        Delete a file or folder in Dropbox (moves to trash).

        Args:
            path: Dropbox path to delete (e.g. /docs/old-report.pdf or /archive).
        """
        try:
            meta = dbx.files_delete_v2(path)
            return json.dumps({
                "status": "success",
                "deleted": meta.metadata.path_display,
            })
        except ApiError as e:
            logger.error(f"delete failed: {e}")
            return json.dumps({"status": "error", "error": str(e)})

    @server.tool()
    def permanently_delete(path: str) -> str:
        """
        Permanently delete a file or folder, bypassing Dropbox trash.

        Args:
            path: Dropbox path to permanently delete.
        """
        try:
            dbx.files_permanently_delete(path)
            return json.dumps({"status": "success", "permanently_deleted": path})
        except ApiError as e:
            logger.error(f"permanently_delete failed: {e}")
            return json.dumps({"status": "error", "error": str(e)})

    @server.tool()
    def get_metadata(path: str) -> str:
        """
        Get metadata for a file or folder (name, size, type, modified date, etc.).

        Args:
            path: Dropbox path (e.g. /docs/report.pdf).
        """
        try:
            meta = dbx.files_get_metadata(path)
            result = {"path": meta.path_display, "name": meta.name}
            if isinstance(meta, dropbox.files.FileMetadata):
                result.update({
                    "type": "file",
                    "size": meta.size,
                    "modified": str(meta.client_modified),
                    "id": meta.id,
                    "rev": meta.rev,
                })
            elif isinstance(meta, dropbox.files.FolderMetadata):
                result["type"] = "folder"
            return json.dumps({"status": "success", **result})
        except ApiError as e:
            logger.error(f"get_metadata failed: {e}")
            return json.dumps({"status": "error", "error": str(e)})

    @server.tool()
    def get_thumbnail(dropbox_path: str, size: str = "w128h128") -> str:
        """
        Get a thumbnail for an image or video file. Returns base64-encoded PNG.

        Args:
            dropbox_path: Path to image/video in Dropbox.
            size: Thumbnail size — w32h32, w64h64, w128h128 (default), w256h256, w480h320, w640h480, w960h640, w1024h768.
        """
        try:
            size_map = {
                "w32h32": dropbox.files.ThumbnailSize.w32h32,
                "w64h64": dropbox.files.ThumbnailSize.w64h64,
                "w128h128": dropbox.files.ThumbnailSize.w128h128,
                "w256h256": dropbox.files.ThumbnailSize.w256h256,
                "w480h320": dropbox.files.ThumbnailSize.w480h320,
                "w640h480": dropbox.files.ThumbnailSize.w640h480,
                "w960h640": dropbox.files.ThumbnailSize.w960h640,
                "w1024h768": dropbox.files.ThumbnailSize.w1024h768,
            }
            thumb_size = size_map.get(size, dropbox.files.ThumbnailSize.w128h128)
            meta, response = dbx.files_get_thumbnail(dropbox_path, size=thumb_size)
            encoded = base64.b64encode(response.content).decode("utf-8")
            return json.dumps({
                "status": "success",
                "path": meta.path_display,
                "size": size,
                "thumbnail_base64": encoded,
            })
        except ApiError as e:
            logger.error(f"get_thumbnail failed: {e}")
            return json.dumps({"status": "error", "error": str(e)})

    @server.tool()
    def get_preview(dropbox_path: str) -> str:
        """
        Get a PDF preview of a file (supports .doc, .docx, .xls, .xlsx, .ppt, .pptx, etc.).
        Returns base64-encoded PDF content.

        Args:
            dropbox_path: Path to the file in Dropbox.
        """
        try:
            meta, response = dbx.files_get_preview(dropbox_path)
            encoded = base64.b64encode(response.content).decode("utf-8")
            return json.dumps({
                "status": "success",
                "path": meta.path_display,
                "preview_pdf_base64": encoded,
            })
        except ApiError as e:
            logger.error(f"get_preview failed: {e}")
            return json.dumps({"status": "error", "error": str(e)})
