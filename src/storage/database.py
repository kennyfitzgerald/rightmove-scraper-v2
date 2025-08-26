import sqlite3
import logging
from datetime import datetime
from typing import List
import os

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS seen_properties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_url TEXT NOT NULL,
    search_config_id TEXT NOT NULL,
    title TEXT,
    price TEXT,
    location TEXT,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(property_url, search_config_id)
);
CREATE INDEX IF NOT EXISTS idx_search_config ON seen_properties(search_config_id);
"""

class PropertyStorage:
    def __init__(self, db_path: str = "/app/data/properties.db"):
        self.db_path = db_path
        self._ensure_db_directory()
        self._init_database()

    def _ensure_db_directory(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def _init_database(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA foreign_keys=ON;")
            # Create table if missing
            conn.executescript(SCHEMA_SQL)
            # If the table exists but with old (property_url) unique constraint, migrate.
            if self._needs_migration(conn):
                self._migrate_unique_constraint(conn)
            conn.commit()
            logger.info("Database initialized successfully")

    def _needs_migration(self, conn: sqlite3.Connection) -> bool:
        # Read the CREATE TABLE SQL to see what UNIQUE is declared as
        row = conn.execute("""
            SELECT sql FROM sqlite_master
            WHERE type='table' AND name='seen_properties'
        """).fetchone()
        if not row or not row[0]:
            return False
        create_sql = row[0]
        # If it already mentions the composite UNIQUE, no migration needed
        if "UNIQUE(property_url, search_config_id)" in create_sql.replace(" ", ""):
            return False
        # If UNIQUE(property_url) is present, we need to migrate
        return "UNIQUE(property_url)" in create_sql.replace(" ", "")

    def _migrate_unique_constraint(self, conn: sqlite3.Connection):
        logger.warning("Migrating seen_properties to composite UNIQUE(property_url, search_config_id)")
        cur = conn.cursor()
        cur.execute("BEGIN IMMEDIATE;")
        # Create new table with correct schema
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS seen_properties_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                property_url TEXT NOT NULL,
                search_config_id TEXT NOT NULL,
                title TEXT,
                price TEXT,
                location TEXT,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(property_url, search_config_id)
            );
        """)
        # Copy data; if duplicates exist per (url, search), keep the earliest first_seen and latest last_seen
        cur.executescript("""
            INSERT OR IGNORE INTO seen_properties_new
            (property_url, search_config_id, title, price, location, first_seen, last_seen)
            SELECT
                property_url,
                COALESCE(search_config_id, ''),  -- guard in case of nulls
                MAX(title),
                MAX(price),
                MAX(location),
                MIN(first_seen),
                MAX(last_seen)
            FROM seen_properties
            GROUP BY property_url, COALESCE(search_config_id, '');
        """)
        # Swap tables
        cur.executescript("""
            DROP TABLE seen_properties;
            ALTER TABLE seen_properties_new RENAME TO seen_properties;
            CREATE INDEX IF NOT EXISTS idx_search_config ON seen_properties(search_config_id);
        """)
        conn.commit()
        logger.info("Migration complete")

    def is_property_seen(self, property_url: str, search_config_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM seen_properties
                WHERE property_url = ? AND search_config_id = ?
            """, (property_url, search_config_id))
            return cursor.fetchone() is not None

    def mark_property_as_seen(self, property_url: str, search_config_id: str,
                              title: str = None, price: str = None, location: str = None):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # UPSERT: insert or refresh last_seen (and metadata if newly provided)
            cursor.execute("""
                INSERT INTO seen_properties (property_url, search_config_id, title, price, location)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(property_url, search_config_id) DO UPDATE SET
                    last_seen = CURRENT_TIMESTAMP,
                    title    = COALESCE(excluded.title, title),
                    price    = COALESCE(excluded.price, price),
                    location = COALESCE(excluded.location, location)
            """, (property_url, search_config_id, title, price, location))
            conn.commit()

    def get_seen_properties(self, search_config_id: str = None) -> List[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            if search_config_id:
                cursor.execute("""
                    SELECT * FROM seen_properties
                    WHERE search_config_id = ?
                    ORDER BY first_seen DESC
                """, (search_config_id,))
            else:
                cursor.execute("SELECT * FROM seen_properties ORDER BY first_seen DESC")
            return [dict(row) for row in cursor.fetchall()]

    def cleanup_old_properties(self, days_old: int = 30):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                DELETE FROM seen_properties
                WHERE last_seen < datetime('now', '-{int(days_old)} days')
            """)
            deleted_count = cursor.rowcount
            conn.commit()
            logger.info(f"Cleaned up {deleted_count} old property records")

    def get_stats(self) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM seen_properties")
            total_properties = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(DISTINCT search_config_id) FROM seen_properties")
            unique_searches = cursor.fetchone()[0]
            cursor.execute("""
                SELECT COUNT(*) FROM seen_properties
                WHERE first_seen > datetime('now', '-1 day')
            """)
            properties_today = cursor.fetchone()[0]
            return {
                "total_properties": total_properties,
                "unique_searches": unique_searches,
                "properties_today": properties_today,
            }
