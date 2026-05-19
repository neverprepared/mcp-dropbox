"""Dropbox SDK client wrapper with OAuth2 refresh token auth."""

import logging
import os

import dropbox
from dropbox.exceptions import AuthError

logger = logging.getLogger(__name__)

class DropboxClient:
    def __init__(self):
        app_key, app_secret, refresh_token = self._validate_config()
        self.dbx = dropbox.Dropbox(
            app_key=app_key,
            app_secret=app_secret,
            oauth2_refresh_token=refresh_token,
        )
        logger.info("Dropbox client initialized")

    def _validate_config(self) -> tuple[str, str, str]:
        vars_ = {
            "DROPBOX_APP_KEY": os.getenv("DROPBOX_APP_KEY"),
            "DROPBOX_APP_SECRET": os.getenv("DROPBOX_APP_SECRET"),
            "DROPBOX_REFRESH_TOKEN": os.getenv("DROPBOX_REFRESH_TOKEN"),
        }
        missing = [k for k, v in vars_.items() if not v]
        if missing:
            raise ValueError(f"Missing required env vars: {', '.join(missing)}")
        return vars_["DROPBOX_APP_KEY"], vars_["DROPBOX_APP_SECRET"], vars_["DROPBOX_REFRESH_TOKEN"]

    def check_auth(self) -> bool:
        try:
            self.dbx.users_get_current_account()
            return True
        except AuthError as e:
            logger.error(f"Auth check failed: {e}")
            return False
