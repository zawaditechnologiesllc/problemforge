"""Refresh the internal active-patent landscape corpus.

Fetches recent (active-era) filings across all configured regions into the
internal-only active_patents table that powers the Validator's aggregate
caution signal. Nothing ingested here is ever shown to users.

Usage: python -m worker.ingest_active
"""

import asyncio

from app.services.active import run_active_ingestion


def main() -> None:
    stats = asyncio.run(run_active_ingestion())
    print(f"Active-landscape ingestion complete: {stats}")


if __name__ == "__main__":
    main()
