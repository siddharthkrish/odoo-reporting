from __future__ import annotations

import os
from typing import Any

from authlib.integrations.starlette_client import OAuth
from google.cloud import firestore
from starlette.requests import Request

oauth = OAuth()


def init_oauth() -> None:
    """Register the Google OIDC client. Call once at app startup."""
    oauth.register(
        name="google",
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


async def is_allowed(email: str) -> bool:
    """Return True if *email* exists in the Firestore allowed_users collection."""
    db = firestore.AsyncClient()
    doc = await db.collection("allowed_users").document(email.lower()).get()
    return doc.exists


def get_session_user(request: Request) -> dict[str, Any] | None:
    """Return the user dict stored in the session, or None if not authenticated."""
    return request.session.get("user")
