import sqlite3

from config import DATABASE_PATH

DATABASE_PATH.parent.mkdir(
    parents=True,
    exist_ok=True
)


def get_connection():

    conn = sqlite3.connect(
        DATABASE_PATH,
        check_same_thread=False
    )

    conn.row_factory = sqlite3.Row

    return conn
