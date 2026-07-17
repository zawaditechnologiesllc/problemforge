"""Embed any blueprints missing vectors (run once after seeding).

Usage: python -m worker.backfill_embeddings
"""

import asyncio

from app.services.ingestion import backfill_embeddings


def main() -> None:
    total = 0
    while True:
        done = asyncio.run(backfill_embeddings())
        total += done
        if done == 0:
            break
    print(f"Backfilled embeddings for {total} blueprints")


if __name__ == "__main__":
    main()
