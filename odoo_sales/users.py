from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone

from dotenv import load_dotenv
from google.cloud import firestore


async def _add(email: str) -> None:
    db = firestore.AsyncClient()
    ref = db.collection("allowed_users").document(email.lower())
    await ref.set({"email": email.lower(), "added_at": datetime.now(timezone.utc)})
    print(f"Added: {email.lower()}")


async def _remove(email: str) -> None:
    db = firestore.AsyncClient()
    ref = db.collection("allowed_users").document(email.lower())
    await ref.delete()
    print(f"Removed: {email.lower()}")


async def _list() -> None:
    db = firestore.AsyncClient()
    docs = db.collection("allowed_users").stream()
    found = False
    async for doc in docs:
        found = True
        data = doc.to_dict()
        added = data.get("added_at", "")
        if isinstance(added, datetime):
            added = added.strftime("%Y-%m-%d %H:%M UTC")
        print(f"  {doc.id}  (added {added})")
    if not found:
        print("  (no allowed users)")


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Manage the Firestore allowed-users list")
    sub = parser.add_subparsers(dest="cmd", required=True)

    add_p = sub.add_parser("add", help="Allow a Google account")
    add_p.add_argument("email")

    rm_p = sub.add_parser("remove", help="Revoke access for a Google account")
    rm_p.add_argument("email")

    sub.add_parser("list", help="List all allowed emails")

    args = parser.parse_args()

    if args.cmd == "add":
        asyncio.run(_add(args.email))
    elif args.cmd == "remove":
        asyncio.run(_remove(args.email))
    elif args.cmd == "list":
        asyncio.run(_list())


if __name__ == "__main__":
    main()
