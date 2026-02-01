#!/usr/bin/env python3
"""
Populate the classical reference database with major authors.

This script adds the major classical authors and their works to the database
when the automated parsing doesn't capture them.
"""

import sqlite3
import os
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass, field


@dataclass
class MajorAuthor:
    """Represents a major classical author."""

    author_id: str
    author_name: str
    cts_namespace: str
    language: str = "lat"
    works: List[Dict[str, str]] = field(default_factory=list)

    def __post_init__(self):
        pass


MAJOR_AUTHORS = [
    MajorAuthor(
        author_id="LAT0474",
        author_name="Marcus Tullius Cicero",
        cts_namespace="phi",
        language="lat",
        works=[
            {
                "canon_id": "phi005",
                "work_title": "De Finibus Bonorum et Malorum",
                "reference": "fin",
                "cts_urn": "urn:cts:latinLit:phi0473.phi005",
            },
            {
                "canon_id": "phi001",
                "work_title": "Epistulae ad Atticum",
                "reference": "att",
                "cts_urn": "urn:cts:latinLit:phi0473.phi001",
            },
            {
                "canon_id": "phi019",
                "work_title": "De Republica",
                "reference": "phil",
                "cts_urn": "urn:cts:latinLit:phi0473.phi019",
            },
            {
                "canon_id": "phi004",
                "work_title": "Tusculanae Disputationes",
                "reference": "tusc",
                "cts_urn": "urn:cts:latinLit:phi0473.phi004",
            },
            {
                "canon_id": "phi002",
                "work_title": "De Oratore",
                "reference": "de orat",
                "cts_urn": "urn:cts:latinLit:phi0473.phi002",
            },
            {
                "canon_id": "phi010",
                "work_title": "In Catilinam",
                "reference": "catil",
                "cts_urn": "urn:cts:latinLit:phi0473.phi010",
            },
            {
                "canon_id": "phi006",
                "work_title": "In Verrem",
                "reference": "verr",
                "cts_urn": "urn:cts:latinLit:phi0473.phi006",
            },
        ],
    ),
    MajorAuthor(
        author_id="LAT0478",
        author_name="Cicero",  # Alternative ID for Cicero
        cts_namespace="phi",
        language="lat",
        works=[
            {
                "canon_id": "phi005",
                "work_title": "De Finibus Bonorum et Malorum",
                "reference": "fin",
                "cts_urn": "urn:cts:latinLit:phi0473.phi005",
            },
            {
                "canon_id": "phi001",
                "work_title": "Epistulae ad Atticum",
                "reference": "att",
                "cts_urn": "urn:cts:latinLit:phi0473.phi001",
            },
            {
                "canon_id": "phi019",
                "work_title": "De Republica",
                "reference": "phil",
                "cts_urn": "urn:cts:latinLit:phi0473.phi019",
            },
            {
                "canon_id": "phi004",
                "work_title": "Tusculanae Disputationes",
                "reference": "tusc",
                "cts_urn": "urn:cts:latinLit:phi0473.phi004",
            },
            {
                "canon_id": "phi002",
                "work_title": "De Oratore",
                "reference": "de orat",
                "cts_urn": "urn:cts:latinLit:phi0473.phi002",
            },
            {
                "canon_id": "phi010",
                "work_title": "In Catilinam",
                "reference": "catil",
                "cts_urn": "urn:cts:latinLit:phi0473.phi010",
            },
            {
                "canon_id": "phi006",
                "work_title": "In Verrem",
                "reference": "verr",
                "cts_urn": "urn:cts:latinLit:phi0473.phi006",
            },
        ],
    ),
    MajorAuthor(
        author_id="LAT1290",
        author_name="Virgil",
        cts_namespace="phi",
        language="lat",
        works=[
            {
                "canon_id": "phi004",
                "work_title": "Aeneid",
                "reference": "aen",
                "cts_urn": "urn:cts:latinLit:phi1290.phi004",
            },
            {
                "canon_id": "phi005",
                "work_title": "Georgics",
                "reference": "georg",
                "cts_urn": "urn:cts:latinLit:phi1290.phi005",
            },
            {
                "canon_id": "phi006",
                "work_title": "Eclogues",
                "reference": "ecl",
                "cts_urn": "urn:cts:latinLit:phi1290.phi006",
            },
        ],
    ),
    MajorAuthor(
        author_id="LAT0831",
        author_name="Horace",
        cts_namespace="phi",
        language="lat",
        works=[
            {
                "canon_id": "phi008",
                "work_title": "Sermones",
                "reference": "s",
                "cts_urn": "urn:cts:latinLit:phi1290.phi008",
            },
            {
                "canon_id": "phi009",
                "work_title": "Epodes",
                "reference": "epod",
                "cts_urn": "urn:cts:latinLit:phi1290.phi009",
            },
            {
                "canon_id": "phi007",
                "work_title": "Odes",
                "reference": "c",
                "cts_urn": "urn:cts:latinLit:phi1290.phi007",
            },
            {
                "canon_id": "phi010",
                "work_title": "Ars Poetica",
                "reference": "ars",
                "cts_urn": "urn:cts:latinLit:phi1290.phi010",
            },
        ],
    ),
    MajorAuthor(
        author_id="LAT0083",
        author_name="Ovid",
        cts_namespace="phi",
        language="lat",
        works=[
            {
                "canon_id": "phi006",
                "work_title": "Amores",
                "reference": "aa",
                "cts_urn": "urn:cts:latinLit:phi1290.phi006",
            },
            {
                "canon_id": "phi001",
                "work_title": "Tristia",
                "reference": "tr",
                "cts_urn": "urn:cts:latinLit:phi1290.phi001",
            },
            {
                "canon_id": "phi002",
                "work_title": "Metamorphoses",
                "reference": "met",
                "cts_urn": "urn:cts:latinLit:phi1290.phi002",
            },
            {
                "canon_id": "phi003",
                "work_title": "Fasti",
                "reference": "fast",
                "cts_urn": "urn:cts:latinLit:phi1290.phi003",
            },
        ],
    ),
    MajorAuthor(
        author_id="LAT1291",
        author_name="Livy",
        cts_namespace="phi",
        language="lat",
        works=[
            {
                "canon_id": "phi001",
                "work_title": "Ab Urbe Condita",
                "reference": "ab urbe condita",
                "cts_urn": "urn:cts:latinLit:phi1291.phi001",
            },
        ],
    ),
    MajorAuthor(
        author_id="LAT0703",
        author_name="Pliny the Elder",
        cts_namespace="phi",
        language="lat",
        works=[
            {
                "canon_id": "phi002",
                "work_title": "Naturalis Historia",
                "reference": "nh",
                "cts_urn": "urn:cts:latinLit:phi1290.phi002",
            },
        ],
    ),
    MajorAuthor(
        author_id="LAT0480",
        author_name="Quintilian",
        cts_namespace="phi",
        language="lat",
        works=[
            {
                "canon_id": "phi003",
                "work_title": "Institutio Oratoria",
                "reference": "inst",
                "cts_urn": "urn:cts:latinLit:phi1290.phi003",
            },
        ],
    ),
    MajorAuthor(
        author_id="LAT0129",
        author_name="Suetonius",
        cts_namespace="phi",
        language="lat",
        works=[
            {
                "canon_id": "phi004",
                "work_title": "De Vita Caesarum",
                "reference": "vit",
                "cts_urn": "urn:cts:latinLit:phi1290.phi004",
            },
        ],
    ),
    MajorAuthor(
        author_id="LAT0702",
        author_name="Martial",
        cts_namespace="phi",
        language="lat",
        works=[
            {
                "canon_id": "phi001",
                "work_title": "Epigrams",
                "reference": "epigr",
                "cts_urn": "urn:cts:latinLit:phi1290.phi001",
            },
        ],
    ),
    MajorAuthor(
        author_id="LAT0210",
        author_name="Statius",
        cts_namespace="phi",
        language="lat",
        works=[
            {
                "canon_id": "phi002",
                "work_title": "Achilleid",
                "reference": "ach",
                "cts_urn": "urn:cts:latinLit:phi1290.phi002",
            },
        ],
    ),
]


def populate_major_authors(db_path: str):
    """Populate the database with major authors and works."""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print(f"Populating database at: {db_path}")

    # Add authors to author_index
    for author in MAJOR_AUTHORS:
        print(f"Adding author: {author.author_name} ({author.author_id})")

        # Check if author already exists
        cursor.execute(
            "SELECT author_id FROM author_index WHERE author_id = ?", (author.author_id,)
        )
        if cursor.fetchone():
            print(f"  Author {author.author_id} already exists, skipping...")
            continue

        # Insert author
        cursor.execute(
            """
            INSERT INTO author_index (author_id, author_name, cts_namespace, language, source)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                author.author_id,
                author.author_name,
                author.cts_namespace,
                author.language,
                "major_authors",
            ),
        )

        # Add works to works table
        for work in author.works:
            print(f"  Adding work: {work['work_title']} ({work['reference']})")

            cursor.execute(
                """
                INSERT OR REPLACE INTO works (canon_id, author_name, work_title, reference, cts_urn, source)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    work["canon_id"],
                    author.author_name,
                    work["work_title"],
                    work["reference"],
                    work["cts_urn"],
                    "major_authors",
                ),
            )

    conn.commit()
    conn.close()

    print("Database population completed!")


def verify_database(db_path: str):
    """Verify the database content."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("\n=== DATABASE VERIFICATION ===")

    # Check authors
    cursor.execute("SELECT author_id, author_name FROM author_index WHERE source = 'major_authors'")
    authors = cursor.fetchall()
    print(f"Major authors added: {len(authors)}")
    for author_id, author_name in authors:
        print(f"  {author_id}: {author_name}")

    # Check works
    cursor.execute(
        "SELECT author_name, work_title, reference FROM works WHERE source = 'major_authors'"
    )
    works = cursor.fetchall()
    print(f"\nWorks added: {len(works)}")
    for author_name, work_title, reference in works[:10]:  # Show first 10
        print(f"  {author_name} - {work_title} ({reference})")
    if len(works) > 10:
        print(f"  ... and {len(works) - 10} more")

    # Check CTS URNs
    cursor.execute(
        "SELECT DISTINCT cts_urn FROM works WHERE cts_urn IS NOT NULL AND source = 'major_authors'"
    )
    urns = cursor.fetchall()
    print(f"\nCTS URNs available: {len(urns)}")
    for urn in urns[:5]:  # Show first 5
        print(f"  {urn[0]}")

    conn.close()


if __name__ == "__main__":
    # Check database path
    db_path = "/tmp/classical_refs_new.db"

    if not os.path.exists(db_path):
        print(f"Database not found at: {db_path}")
        print("Please run the database build script first.")
        exit(1)

    populate_major_authors(db_path)
    verify_database(db_path)
