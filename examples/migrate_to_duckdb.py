#!/usr/bin/env python3
"""
DuckDB Migration Script for CTS URN Database.

This script migrates the SQLite CTS URN database to DuckDB format,
providing better performance and integration with modern data processing.
"""

import os
import sys
import sqlite3
import duckdb
import shutil
from pathlib import Path
from typing import Optional, Union
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class DuckDBMigrator:
    """Handles migration from SQLite to DuckDB for CTS URN database."""

    def __init__(self, sqlite_path: str, duckdb_path: str):
        self.sqlite_path = sqlite_path
        self.duckdb_path = duckdb_path
        self.backup_path = f"{sqlite_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def validate_source_database(self) -> bool:
        """Validate that the source SQLite database exists and has required tables."""
        if not os.path.exists(self.sqlite_path):
            logger.error(f"Source database not found: {self.sqlite_path}")
            return False

        try:
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()

            # Check for required tables
            required_tables = ["author_index", "works", "unified_index"]
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = [row[0] for row in cursor.fetchall()]

            for table in required_tables:
                if table not in existing_tables:
                    logger.error(f"Required table missing: {table}")
                    return False

            conn.close()
            logger.info("Source database validation successful")
            return True

        except Exception as e:
            logger.error(f"Source database validation failed: {e}")
            return False

    def create_backup(self) -> bool:
        """Create a backup of the SQLite database."""
        try:
            if os.path.exists(self.backup_path):
                logger.warning(f"Backup already exists: {self.backup_path}")
                return True

            # Copy the database file
            shutil.copy2(self.sqlite_path, self.backup_path)
            logger.info(f"Backup created: {self.backup_path}")
            return True

        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            return False

    def migrate_database(self) -> bool:
        """Migrate SQLite database to DuckDB."""
        try:
            logger.info("Starting database migration...")

            # Connect to SQLite
            sqlite_conn = sqlite3.connect(self.sqlite_path)

            # Connect to DuckDB
            duckdb_conn = duckdb.connect(self.duckdb_path)

            # Get all tables from SQLite
            cursor = sqlite_conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()

            logger.info(f"Found {len(tables)} tables to migrate")

            for table in tables:
                table_name = table[0]
                logger.info(f"Migrating table: {table_name}")

                # Read data from SQLite
                cursor.execute(f"SELECT * FROM {table_name}")
                rows = cursor.fetchall()

                # Get column names and types
                cursor.execute(f"PRAGMA table_info({table_name})")
                col_info = cursor.fetchall()

                # Log table info
                logger.info(f"  - {table_name}: {len(rows)} rows, {len(col_info)} columns")

                if rows:
                    # Create table structure first
                    col_defs = []
                    for col in col_info:
                        # col format: cid, name, type, notnull, dflt_value, pk
                        col_name = col[1]
                        col_type = col[2].upper()
                        if "INTEGER" in col_type:
                            col_type = "BIGINT"
                        elif "TEXT" in col_type or "VARCHAR" in col_type:
                            col_type = "VARCHAR"
                        elif "REAL" in col_type:
                            col_type = "DOUBLE"
                        elif "BLOB" in col_type:
                            col_type = "BLOB"

                        # Handle primary key and constraints
                        constraints = []
                        if col[3]:  # NOT NULL
                            constraints.append("NOT NULL")
                        if col[5]:  # PRIMARY KEY
                            constraints.append("PRIMARY KEY")

                        col_def = f"{col_name} {col_type}"
                        if constraints:
                            col_def += " " + " ".join(constraints)
                        col_defs.append(col_def)

                    create_table_sql = f"CREATE TABLE {table_name} ({', '.join(col_defs)})"
                    duckdb_conn.execute(create_table_sql)

                    # Insert data
                    placeholders = ", ".join(["?"] * len(col_info))
                    insert_sql = f"INSERT INTO {table_name} VALUES ({placeholders})"
                    duckdb_conn.executemany(insert_sql, rows)

                # Create indexes for frequently queried columns
                if table_name == "author_index":
                    duckdb_conn.execute(
                        f"CREATE INDEX IF NOT EXISTS idx_author_name ON {table_name}(author_name)"
                    )
                    duckdb_conn.execute(
                        f"CREATE INDEX IF NOT EXISTS idx_cts_namespace ON {table_name}(cts_namespace)"
                    )
                elif table_name == "works":
                    duckdb_conn.execute(
                        f"CREATE INDEX IF NOT EXISTS idx_work_title ON {table_name}(work_title)"
                    )
                    duckdb_conn.execute(
                        f"CREATE INDEX IF NOT EXISTS idx_author_work ON {table_name}(author_name, work_title)"
                    )
                    duckdb_conn.execute(
                        f"CREATE INDEX IF NOT EXISTS idx_cts_urn ON {table_name}(cts_urn)"
                    )

            # Close connections
            sqlite_conn.close()
            duckdb_conn.close()

            logger.info("Database migration completed successfully!")
            return True

        except Exception as e:
            logger.error(f"Database migration failed: {e}")
            return False

    def validate_migration(self) -> bool:
        """Validate that the migration was successful."""
        try:
            if not os.path.exists(self.duckdb_path):
                logger.error("DuckDB database was not created")
                return False

            # Connect to both databases for comparison
            sqlite_conn = sqlite3.connect(self.sqlite_path)
            duckdb_conn = duckdb.connect(self.duckdb_path)

            # Compare row counts for each table
            cursor = sqlite_conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()

            all_valid = True

            for table in tables:
                table_name = table[0]

                # Get SQLite row count
                sqlite_cursor = sqlite_conn.cursor()
                sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                sqlite_count = sqlite_cursor.fetchone()[0]

                # Get DuckDB row count
                duckdb_result = duckdb_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
                if duckdb_result:
                    duckdb_count = duckdb_result[0]
                else:
                    duckdb_count = 0

                if sqlite_count != duckdb_count:
                    logger.error(
                        f"Row count mismatch for {table_name}: SQLite={sqlite_count}, DuckDB={duckdb_count}"
                    )
                    all_valid = False
                else:
                    logger.info(f"✓ {table_name}: {sqlite_count} rows (match)")

            # Test basic functionality
            try:
                # Test a simple query
                result = duckdb_conn.execute(
                    "SELECT author_name, COUNT(*) as works_count FROM works GROUP BY author_name LIMIT 5"
                )
                rows = result.fetchall()
                logger.info(f"Sample query result: {len(rows)} rows")

                # Test CTS URN mapping
                test_result = duckdb_conn.execute(
                    "SELECT cts_urn FROM works WHERE author_name = 'Livy' AND work_title = 'Ab Urbe Condita' LIMIT 1"
                ).fetchone()
                if test_result:
                    logger.info(f"CTS URN test: {test_result[0]}")
                else:
                    logger.warning("No CTS URN found for Livy Ab Urbe Condita")

            except Exception as e:
                logger.error(f"Functionality test failed: {e}")
                all_valid = False

            sqlite_conn.close()
            duckdb_conn.close()

            if all_valid:
                logger.info("Migration validation successful!")
            else:
                logger.error("Migration validation failed!")

            return all_valid

        except Exception as e:
            logger.error(f"Migration validation failed: {e}")
            return False

    def cleanup(self) -> bool:
        """Clean up temporary files and backups if migration was successful."""
        try:
            # Ask user if they want to keep the backup
            response = input("Migration successful! Keep SQLite backup? (y/N): ").strip().lower()
            if response != "y":
                try:
                    os.remove(self.backup_path)
                    logger.info(f"Backup removed: {self.backup_path}")
                except Exception as e:
                    logger.warning(f"Could not remove backup: {e}")

            return True

        except KeyboardInterrupt:
            logger.info("Cleanup interrupted by user")
            return False
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return False


def main():
    """Main migration function."""
    # Define paths
    sqlite_path = "/tmp/classical_refs_new.db"
    duckdb_path = "/tmp/classical_refs.duckdb"

    logger.info("🚀 DuckDB Migration for CTS URN Database")
    logger.info("=" * 60)

    # Create migrator
    migrator = DuckDBMigrator(sqlite_path, duckdb_path)

    # Step 1: Validate source
    if not migrator.validate_source_database():
        logger.error("Source database validation failed. Aborting migration.")
        sys.exit(1)

    # Step 2: Create backup
    if not migrator.create_backup():
        logger.error("Backup creation failed. Aborting migration.")
        sys.exit(1)

    # Step 3: Migrate database
    if not migrator.migrate_database():
        logger.error("Database migration failed. Check logs for details.")
        sys.exit(1)

    # Step 4: Validate migration
    if not migrator.validate_migration():
        logger.error("Migration validation failed. Check logs for details.")
        sys.exit(1)

    # Step 5: Cleanup
    if not migrator.cleanup():
        logger.error("Cleanup failed.")
        sys.exit(1)

    logger.info("🎉 Migration completed successfully!")
    logger.info(f"New DuckDB database: {duckdb_path}")
    logger.info("Ready to use with updated CTSUrnMapper!")


if __name__ == "__main__":
    main()
