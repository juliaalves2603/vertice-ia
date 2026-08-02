import os
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DB_PATH = Path(
    os.getenv(
        "VERTICE_DB_PATH",
        str(BASE_DIR / "vertice_ia_limpa.db")
    )
)
def db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c
def init_db():
    with db() as c:
        c.execute('''CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL, source TEXT,
            facebook_page_id TEXT, facebook_page_name TEXT, instagram_account_id TEXT, instagram_username TEXT,
            total_posts INTEGER DEFAULT 0, alcance_total INTEGER DEFAULT 0, salvos_total INTEGER DEFAULT 0,
            shares_total INTEGER DEFAULT 0, comentarios_total INTEGER DEFAULT 0, curtidas_total INTEGER DEFAULT 0,
            raw_summary TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS snapshot_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT, snapshot_id INTEGER NOT NULL, post_id TEXT NOT NULL,
            caption TEXT, media_type TEXT, media_product_type TEXT, permalink TEXT, timestamp TEXT,
            like_count INTEGER DEFAULT 0, comments_count INTEGER DEFAULT 0, reach INTEGER DEFAULT 0,
            saved INTEGER DEFAULT 0, shares INTEGER DEFAULT 0, engagement_rate REAL DEFAULT 0,
            potential_score REAL DEFAULT 0, raw_post TEXT)''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_snapshots_created ON snapshots(created_at)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_posts_snapshot ON snapshot_posts(snapshot_id)')
        c.commit()