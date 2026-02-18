from __future__ import annotations

from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .client import OdooClient

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Odoo Sales Reporter")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/sales")
def sales(
    date_from: str = Query(..., alias="from", description="Start date (YYYY-MM-DD)"),
    date_to: str = Query(..., alias="to", description="End date (YYYY-MM-DD)"),
) -> list[dict]:
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
