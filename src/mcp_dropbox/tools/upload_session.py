"""Upload session tools for files >150MB: start, append, finish."""

import json
import logging
import os

import dropbox
from dropbox.exceptions import ApiError
from mcp.server.fastmcp import FastMCP

from ..client import DropboxClient

logger = logging.getLogger(__name__)

CHUNK_SIZE = 150 * 1024 * 1024  # 150MB chunks


def register_upload_session_tools(server: FastMCP, client: DropboxClient) -> None:
    dbx = client.dbx

    @server.tool()
    def upload_session_start(local_path: str) -> str:
        """
        Start an upload session for a large file (>150MB). Uploads the first chunk.
        Returns a session_id and offset to use with upload_session_append/finish.

        Args:
            local_path: Absolute path to the local file to upload.
        """
        try:
            with open(local_path, "rb") as f:
                chunk = f.read(CHUNK_SIZE)
                result = dbx.files_upload_session_start(chunk)
                offset = len(chunk)
            return json.dumps({
                "status": "success",
                "session_id": result.session_id,
                "offset": offset,
                "local_path": local_path,
                "file_size": os.path.getsize(local_path),
            })
        except ApiError as e:
            logger.error(f"upload_session_start failed: {e}")
            return json.dumps({"status": "error", "error": str(e)})
        except FileNotFoundError:
            return json.dumps({"status": "error", "error": f"Local file not found: {local_path}"})

    @server.tool()
    def upload_session_append(local_path: str, session_id: str, offset: int) -> str:
        """
        Append the next chunk to an in-progress upload session.
        Call repeatedly until all data is uploaded, then call upload_session_finish.

        Args:
            local_path: Absolute path to the local file being uploaded.
            session_id: Session ID returned by upload_session_start.
            offset: Byte offset where this chunk starts (returned by previous call).
        """
        try:
            cursor = dropbox.files.UploadSessionCursor(
                session_id=session_id, offset=offset
            )
            with open(local_path, "rb") as f:
                f.seek(offset)
                chunk = f.read(CHUNK_SIZE)

            if not chunk:
                return json.dumps({
                    "status": "success",
                    "note": "No more data to append. Call upload_session_finish.",
                    "session_id": session_id,
                    "offset": offset,
                })

            dbx.files_upload_session_append_v2(chunk, cursor)
            new_offset = offset + len(chunk)
            file_size = os.path.getsize(local_path)

            return json.dumps({
                "status": "success",
                "session_id": session_id,
                "offset": new_offset,
                "file_size": file_size,
                "done": new_offset >= file_size,
            })
        except ApiError as e:
            logger.error(f"upload_session_append failed: {e}")
            return json.dumps({"status": "error", "error": str(e)})

    @server.tool()
    def upload_session_finish(
        local_path: str,
        session_id: str,
        offset: int,
        dropbox_path: str,
        overwrite: bool = True,
    ) -> str:
        """
        Finish an upload session and commit the file to Dropbox.
        Call after all chunks have been appended via upload_session_append.

        Args:
            local_path: Absolute path to the local file (used to read the final chunk).
            session_id: Session ID from upload_session_start.
            offset: Final byte offset (returned by last upload_session_append call).
            dropbox_path: Destination path in Dropbox (e.g. /videos/large-file.mp4).
            overwrite: Replace existing file if True (default).
        """
        try:
            cursor = dropbox.files.UploadSessionCursor(
                session_id=session_id, offset=offset
            )
            mode = (
                dropbox.files.WriteMode.overwrite
                if overwrite
                else dropbox.files.WriteMode.add
            )
            commit = dropbox.files.CommitInfo(path=dropbox_path, mode=mode)

            with open(local_path, "rb") as f:
                f.seek(offset)
                final_chunk = f.read()

            meta = dbx.files_upload_session_finish(final_chunk, cursor, commit)
            return json.dumps({
                "status": "success",
                "path": meta.path_display,
                "size": meta.size,
                "id": meta.id,
            })
        except ApiError as e:
            logger.error(f"upload_session_finish failed: {e}")
            return json.dumps({"status": "error", "error": str(e)})
