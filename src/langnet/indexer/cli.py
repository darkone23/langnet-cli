"""
Indexer CLI commands for langnet-cli.

This module provides command-line interface for building and managing search indexes.
"""

import logging
import sys
from pathlib import Path

import click

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from langnet.indexer.core import IndexType
    from langnet.indexer.cts_urn_indexer import CtsUrnIndexer
    from langnet.indexer.utils import IndexManager, get_index_manager
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure the indexer modules are properly installed")
    sys.exit(1)

logger = logging.getLogger(__name__)

index_manager: IndexManager | None = None  # Global index manager instance


# Indexer group - will be added to main CLI
@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--config-dir", type=click.Path(), help="Configuration directory")
def indexer(verbose: bool, config_dir: str | None):
    """Indexer tools for building and managing search indexes."""
    if verbose:
        logging.basicConfig(level=logging.INFO)

    # Initialize index manager
    if config_dir:
        from .utils import IndexManager  # noqa: PLC0415

        global index_manager  # noqa: PLW0603
        index_manager = IndexManager(Path(config_dir))
    else:
        index_manager = get_index_manager()


def register_indexer_commands(main_cli: click.Group):
    """Register indexer commands with the main CLI."""
    main_cli.add_command(indexer, "indexer")


@indexer.group()
def build():
    """Build search indexes from source data."""
    pass


@build.command("cts-urn")
@click.option(
    "--perseus-dir",
    "--source",
    "-s",
    "perseus_dir",
    type=click.Path(exists=True),
    default=str(Path.home() / "perseus"),
    help="Perseus corpus root (expects canonical-latinLit and canonical-greekLit under this path)",
    show_default=True,
)
@click.option("--output", "-o", type=click.Path(), help="Output database path")
@click.option(
    "--wipe/--no-wipe",
    default=True,
    help="Delete any existing CTS index file before rebuilding",
    show_default=True,
)
@click.option("--force", is_flag=True, help="Force rebuild even if index exists")
@click.option("--config-dir", type=click.Path(), help="Configuration directory")
def build_cts_urn(
    perseus_dir: str, output: str | None, wipe: bool, force: bool, config_dir: str | None
):
    """Build CTS URN reference index."""
    source_path = Path(perseus_dir)
    output_path = (
        Path(output) if output else Path.home() / ".local" / "share" / "langnet" / "cts_urn.duckdb"
    )

    # Create output directory if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists() and wipe:
        output_path.unlink()
        click.echo(f"Deleted existing index file {output_path}")
    elif output_path.exists() and not force:
        click.echo(f"Index already exists at {output_path}. Use --wipe or --force to rebuild.")
        return 1

    click.echo("Building CTS URN index...")
    click.echo(f"Source: {source_path}")
    click.echo(f"Output: {output_path}")

    # Build indexer
    config = {"perseus_dir": str(source_path), "force_rebuild": force, "wipe_existing": wipe}

    indexer = CtsUrnIndexer(output_path, config)

    try:
        success = indexer.build()
        if success:
            click.echo("✅ CTS URN index built successfully!")

            # Register the index
            assert index_manager is not None
            index_manager.register_index(
                name="cts_urn", index_type=IndexType.CTS_URN, path=output_path, config=config
            )

            # Show stats
            stats = indexer.get_stats()
            work_count = stats.get("work_count", "N/A")
            size_mb = stats.get("size_mb", 0)
            click.echo(f"📊 Stats: {work_count} works, {size_mb:.2f} MB")
            perseus = stats.get("perseus_count", "?")
            legacy = stats.get("legacy_count", "?")
            supplements = stats.get("supplement_count", "?")
            click.echo(f"    Perseus: {perseus} | Legacy gaps: {legacy} | Supplemental: {supplements}")
        else:
            click.echo("❌ Failed to build CTS URN index")
            return 1
    except Exception as e:
        click.echo(f"❌ Error building index: {e}")
        return 1
    finally:
        indexer.cleanup()

    return 0


@indexer.group()
def stats():
    """Show index statistics."""
    pass


@stats.command("cts-urn")
@click.option("--name", "-n", default="cts_urn", help="Index name")
def stats_cts_urn(name: str):
    """Show CTS URN index statistics."""
    from .utils import IndexManager  # noqa: PLC0415

    manager = IndexManager()
    stats = manager.get_index_stats(name)

    if not stats:
        click.echo(f"❌ Index '{name}' not found")
        return 1

    click.echo(f"📊 {name} Index Statistics:")
    click.echo(f"  Type: {stats.index_type.value}")
    click.echo(f"  Status: {stats.status.value}")
    click.echo(f"  Size: {stats.size_mb:.2f} MB")
    click.echo(f"  Entries: {stats.entry_count}")
    click.echo(f"  Built: {stats.build_date}")

    return 0


@indexer.command("list")
def list_indexes():
    """List all registered indexes."""
    from .utils import IndexManager  # noqa: PLC0415

    manager = IndexManager()
    indexes = manager.list_indexes()

    if not indexes:
        click.echo("No indexes registered")
        return 0

    click.echo("📋 Registered Indexes:")
    for idx in indexes:
        click.echo(f"  {idx['type']:12} {idx['path']}")

    return 0


@indexer.command("query")
@click.argument("abbrev")
@click.option("--type", "-t", type=click.Choice(["cts-urn"]), default="cts-urn", help="Index type")
@click.option("--language", "-l", default="lat", help="Language code")
def query(abbrev: str, type: str, language: str):
    """Query an index for abbreviation matches."""
    if type != "cts-urn":
        click.echo(f"❌ Query type '{type}' not implemented yet")
        return 1

    # Load CTS URN index
    from .utils import IndexManager  # noqa: PLC0415

    manager = IndexManager()
    config = manager.get_index_config("cts_urn")

    if not config:
        click.echo("❌ CTS URN index not found. Run 'langnet-cli indexer build cts-urn' first.")
        return 1

    output_path = Path(config["path"])
    if not output_path.exists():
        click.echo("❌ CTS URN index file not found")
        return 1

    # Query the index
    indexer = CtsUrnIndexer(output_path, config)
    try:
        results = indexer.query_abbreviation(abbrev, language)

        if not results:
            click.echo(f"❌ No matches found for '{abbrev}'")
        else:
            click.echo(f"🔍 Results for '{abbrev}':")
            for result in results:
                click.echo(f"  {result}")

    except Exception as e:
        click.echo(f"❌ Query error: {e}")
        return 1
    finally:
        indexer.cleanup()

    return 0


@indexer.command("validate")
@click.option("--type", "-t", type=click.Choice(["cts-urn"]), default="cts-urn", help="Index type")
@click.option("--fix", is_flag=True, help="Attempt to fix issues")
def validate(type: str, fix: bool):
    """Validate index integrity."""
    if type != "cts-urn":
        click.echo(f"❌ Validation for '{type}' not implemented yet")
        return 1

    # Load CTS URN index
    from .utils import IndexManager  # noqa: PLC0415

    manager = IndexManager()
    config = manager.get_index_config("cts-urn")

    if not config:
        click.echo("❌ CTS URN index not found")
        return 1

    output_path = Path(config["path"])
    if not output_path.exists():
        click.echo("❌ CTS URN index file not found")
        return 1

    # Validate the index
    indexer = CtsUrnIndexer(output_path, config)
    try:
        is_valid = indexer.validate()

        if is_valid:
            click.echo("✅ Index validation passed")
        else:
            click.echo("❌ Index validation failed")
            if fix:
                click.echo("💡 Fix mode not implemented yet")
            return 1

    except Exception as e:
        click.echo(f"❌ Validation error: {e}")
        return 1
    finally:
        indexer.cleanup()

    return 0
