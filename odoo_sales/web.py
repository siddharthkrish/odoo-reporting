from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request

load_dotenv()

from .auth import get_session_user, init_oauth, is_allowed, oauth  # noqa: E402
from .client import OdooClient  # noqa: E402

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Odoo Sales Reporter")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET", "change-me-in-production"),
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.on_event("startup")
async def startup() -> None:
    init_oauth()


# ── Auth helpers ──────────────────────────────────────────────────────────────

def _require_auth(request: Request) -> dict[str, Any]:
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# ── Public routes ─────────────────────────────────────────────────────────────

@app.get("/login", include_in_schema=False)
async def login_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "login.html")


@app.get("/auth/google", include_in_schema=False)
async def auth_google(request: Request):
    redirect_uri = request.url_for("auth_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/auth/callback", include_in_schema=False)
async def auth_callback(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception:
        return RedirectResponse("/login?error=auth_failed")

    user_info = token.get("userinfo")
    if not user_info:
        return RedirectResponse("/login?error=auth_failed")

    email = user_info.get("email", "").lower()
    if not email:
        return RedirectResponse("/login?error=auth_failed")

    if not await is_allowed(email):
        return RedirectResponse("/login?error=not_allowed")

    request.session["user"] = {
        "email": email,
        "name": user_info.get("name", email),
        "picture": user_info.get("picture", ""),
    }
    return RedirectResponse("/")


@app.get("/logout", include_in_schema=False)
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login")


# ── Protected routes ──────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def index(request: Request) -> FileResponse:
    if not get_session_user(request):
        return RedirectResponse("/login")
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/me")
async def me(request: Request) -> dict[str, Any]:
    return _require_auth(request)


@app.get("/api/sales")
def sales(
    request: Request,
    date_from: str = Query(..., alias="from", description="Start date (YYYY-MM-DD)"),
    date_to: str = Query(..., alias="to", description="End date (YYYY-MM-DD)"),
) -> list[dict]:
    _require_auth(request)
    try:
        client = OdooClient.from_env()
        orders = client.get_sales_data(date_from, date_to)
        return [order.to_dict() for order in orders]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def main() -> None:
    uvicorn.run("odoo_sales.web:app", host="127.0.0.1", port=8000, reload=True)


if __name__ == "__main__":
    main()
