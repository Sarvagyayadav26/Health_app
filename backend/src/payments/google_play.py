import logging
from typing import Optional

from src.utils import config

logger = logging.getLogger("backend")

try:
    # Lazy import google libraries; if missing a clear error will be raised
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
except Exception as e:
    service_account = None
    build = None
    logger.debug("Google Play client libraries not available: %s", e)


def verify_product_purchase(package_name: str, product_id: str, token: str) -> Optional[dict]:
    """Verify a one-time in-app product purchase with Google Play.

    Returns the Google Play API response (dict) on success, or None if
    verification could not be performed (e.g. missing config).
    Raises exceptions on fatal errors.
    """
    if not config.GOOGLE_SERVICE_ACCOUNT_FILE or not package_name:
        logger.debug("Google Play verification skipped - missing configuration")
        return None

    if service_account is None or build is None:
        raise RuntimeError("google-auth/google-api-python-client not installed")

    creds = service_account.Credentials.from_service_account_file(
        config.GOOGLE_SERVICE_ACCOUNT_FILE,
        scopes=["https://www.googleapis.com/auth/androidpublisher"],
    )

    service = build("androidpublisher", "v3", credentials=creds, cache_discovery=False)

    try:
        resp = service.purchases().products().get(
            packageName=package_name,
            productId=product_id,
            token=token
        ).execute()
        logger.debug("Google Play verify response: %s", resp)
        return resp
    except Exception:
        logger.exception("Google Play verification call failed")
        raise
