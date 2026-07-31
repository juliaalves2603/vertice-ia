from database import get_connection


def init_database():

    with get_connection() as conn:

        conn.execute("""

        CREATE TABLE IF NOT EXISTS snapshots(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            created_at TEXT,

            source TEXT,

            facebook_page_id TEXT,

            facebook_page_name TEXT,

            instagram_account_id TEXT,

            instagram_username TEXT,

            total_posts INTEGER,

            alcance_total INTEGER,

            salvos_total INTEGER,

            shares_total INTEGER,

            comentarios_total INTEGER,

            curtidas_total INTEGER,

            raw_summary TEXT

        )

        """)

        conn.commit()
        