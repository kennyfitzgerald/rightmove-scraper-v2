import sqlite3
import logging
from datetime import datetime
from typing import List, Set
import os

logger = logging.getLogger(__name__)

class PropertyStorage:
    def __init__(self, db_path: str = "/app/data/properties.db"):
        self.db_path = db_path
        self._ensure_db_directory()
        self._init_database()
        
    def _ensure_db_directory(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
    def _init_database(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS seen_properties (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    property_url TEXT UNIQUE NOT NULL,
                    search_config_id TEXT NOT NULL,
                    title TEXT,
                    price TEXT,
                    location TEXT,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_property_url 
                ON seen_properties(property_url)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_search_config 
                ON seen_properties(search_config_id)
            """)
            
            conn.commit()
            logger.info("Database initialized successfully")
            
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
            
            # Check if already exists
            cursor.execute("""
                SELECT id FROM seen_properties 
                WHERE property_url = ? AND search_config_id = ?
            """, (property_url, search_config_id))
            
            if cursor.fetchone():
                # Update last_seen timestamp
                cursor.execute("""
                    UPDATE seen_properties 
                    SET last_seen = CURRENT_TIMESTAMP 
                    WHERE property_url = ? AND search_config_id = ?
                """, (property_url, search_config_id))
            else:
                # Insert new record
                cursor.execute("""
                    INSERT INTO seen_properties 
                    (property_url, search_config_id, title, price, location) 
                    VALUES (?, ?, ?, ?, ?)
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
                cursor.execute("""
                    SELECT * FROM seen_properties 
                    ORDER BY first_seen DESC
                """)
                
            return [dict(row) for row in cursor.fetchall()]
            
    def cleanup_old_properties(self, days_old: int = 30):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM seen_properties 
                WHERE last_seen < datetime('now', '-{} days')
            """.format(days_old))
            
            deleted_count = cursor.rowcount
            conn.commit()
            logger.info(f"Cleaned up {deleted_count} old property records")
            
    def get_stats(self) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM seen_properties")
            total_properties = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(DISTINCT search_config_id) 
                FROM seen_properties
            """)
            unique_searches = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM seen_properties 
                WHERE first_seen > datetime('now', '-1 day')
            """)
            properties_today = cursor.fetchone()[0]
            
            return {
                'total_properties': total_properties,
                'unique_searches': unique_searches,
                'properties_today': properties_today
            }