"""Weekly ingestion entrypoint — run by the Render cron job.

Usage: python -m worker.ingest
"""

import asyncio

from app.services.ingestion import run_ingestion


def main() -> None:
    stats = asyncio.run(run_ingestion())
    print(f"Ingestion complete: {stats}")


if __name__ == "__main__":
    main()
