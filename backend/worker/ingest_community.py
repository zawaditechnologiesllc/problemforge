"""Refresh the startup-community corpus from public old.reddit pages.

Pulls the month's top posts from the startup-idea communities listed in
services/community.py, embeds them, and stores them (idempotent by URL).

Usage: python -m worker.ingest_community
"""

import asyncio

from app.services.community import run_community_ingestion


def main() -> None:
    stats = asyncio.run(run_community_ingestion())
    print(f"Community ingestion complete: {stats}")


if __name__ == "__main__":
    main()
