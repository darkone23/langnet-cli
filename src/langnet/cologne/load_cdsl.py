#!/usr/bin/env python3
"""
CDSL Dictionary Loader

Usage:
    python -m langnet.cologne.load_cdsl <dict_id>
        [--limit N] [--force] [--batch-size N] [--workers N]

Examples:
    python -m langnet.cologne.load_cdsl MW           # Load full MW dictionary
    python -m langnet.cologne.load_cdsl MW --limit 1000  # Load first 1000 entries
    python -m langnet.cologne.load_cdsl AP90 --force  # Rebuild AP90 from scratch
    python -m langnet.cologne.load_cdsl AP90 --batch-size 1000 --workers 4
"""

import sys
from pathlib import Path

import click
import structlog

from langnet.cologne.core import CdslIndexBuilder
from langnet.config import config

structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(20),
)

logger = structlog.get_logger()


@click.command()
@click.argument("dict_id", type=str)
@click.option("--limit", default=None, type=int, help="Limit to N entries (for testing)")
@click.option("--force", is_flag=True, default=False, help="Overwrite existing database")
@click.option(
    "--batch-size",
    default=None,
    type=int,
    help="Batch size for processing (default: auto)",
)
@click.option(
    "--workers",
    default=None,
    type=int,
    help="Number of parallel workers (default: CPU count)",
)
def load_cdsl(
    dict_id: str,
    limit: int | None,
    force: bool,
    batch_size: int | None,
    workers: int | None,
):
    """Load a CDSL dictionary into DuckDB."""
    sys.path.insert(0, str(Path(__file__).parent.parent))

    dict_id = dict_id.upper()
    dict_dir = config.cdsl_dict_dir / dict_id
    output_db = config.cdsl_db_dir / f"{dict_id.lower()}.db"

    if not dict_dir.exists():
        logger.error("dict_dir_not_found", dict_id=dict_id, path=str(dict_dir))
        raise click.ClickException(f"Dictionary directory not found: {dict_dir}")

    logger.info(
        "loading_dictionary",
        dict_id=dict_id,
        dict_dir=str(dict_dir),
        output_db=str(output_db),
    )

    if output_db.exists() and not force:
        logger.warning("db_exists_use_force", dict_id=dict_id, path=str(output_db))
        raise click.ClickException(f"Database exists: {output_db}. Use --force to overwrite.")

    try:
        count = CdslIndexBuilder.build(
            dict_dir,
            output_db,
            dict_id,
            limit=limit,
            batch_size=batch_size,
            num_workers=workers,
        )
        logger.info("load_complete", dict_id=dict_id, entries=count)
        click.echo(f"Successfully loaded {count} entries from {dict_id}")
    except Exception as e:
        logger.error("load_failed", dict_id=dict_id, error=str(e))
        raise click.ClickException(f"Failed to load {dict_id}: {e}")


if __name__ == "__main__":
    load_cdsl()
