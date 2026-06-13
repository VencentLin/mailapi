"""Bootstrap and admin management commands.

Usage:

    python -m backend.app.cli create-admin

Reads the following environment variables (or .env):

- INIT_ADMIN_USERNAME
- INIT_ADMIN_PASSWORD
- INIT_ADMIN_EMAIL

If a user with the given username already exists, prints a notice and exits
without modifying anything.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from backend.app.core.config import get_settings
from backend.app.db.session import AsyncSessionLocal
from backend.app.services.users import ensure_admin_user


async def _create_admin() -> None:
    settings = get_settings()
    username = settings.init_admin_username
    password = settings.init_admin_password
    email = settings.init_admin_email

    if not username or not password or not email:
        print(
            "ERROR: INIT_ADMIN_USERNAME, INIT_ADMIN_PASSWORD and INIT_ADMIN_EMAIL "
            "must all be set in .env or environment.",
            file=sys.stderr,
        )
        sys.exit(1)

    async with AsyncSessionLocal() as session:
        user, created = await ensure_admin_user(
            session,
            username=username,
            email=email,
            password=password,
        )

    if created:
        print(f"Admin user '{user.username}' created with role '{user.role.value}'.")
    else:
        print(f"Admin user '{user.username}' already exists; skipping.")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="MailAPI admin CLI")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("create-admin", help="Create the bootstrap admin user from environment values")

    args = parser.parse_args(argv or sys.argv[1:])

    if args.command == "create-admin":
        asyncio.run(_create_admin())
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
