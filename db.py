import sqlite3
import os
import config

USING_PG = bool(config.DATABASE_URL)

def get_db():
    if USING_PG:
        return _pg_connect()
    return _sqlite_connect()

# -----------------------------------------------------------------------
# SQLite
# -----------------------------------------------------------------------
def _sqlite_connect():
    os.makedirs(os.path.dirname(config.DB_PATH), exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return _wrap(conn, is_pg=False)

# -----------------------------------------------------------------------
# PostgreSQL (Supabase)
# -----------------------------------------------------------------------
def _pg_connect():
    import psycopg2
    from psycopg2.extras import RealDictCursor
    conn = psycopg2.connect(config.DATABASE_URL)
    conn.autocommit = False
    return _wrap(conn, is_pg=True, cursor_factory=RealDictCursor)

# -----------------------------------------------------------------------
# Wrapper unificado
# -----------------------------------------------------------------------
class _DB:
    def __init__(self, conn, is_pg, cursor_factory=None):
        self._conn = conn
        self._is_pg = is_pg
        self._cursor_factory = cursor_factory

    def execute(self, sql, params=None):
        sql = sql.replace('%s', '?') if not self._is_pg and params else sql
        cur = self._conn.cursor(cursor_factory=self._cursor_factory) if self._is_pg else self._conn.cursor()
        try:
            cur.execute(sql, params or ())
        except Exception as e:
            err_str = str(e).lower()
            if 'unique' in err_str or 'integrity' in err_str:
                raise IntegrityError()
            raise
        return cur

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()

def _wrap(conn, is_pg, cursor_factory=None):
    return _DB(conn, is_pg, cursor_factory)

# -----------------------------------------------------------------------
# Init
# -----------------------------------------------------------------------
def init_db():
    conn = get_db()

    if USING_PG:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS equipamentos (
                id SERIAL PRIMARY KEY,
                codigo TEXT NOT NULL UNIQUE,
                regional TEXT NOT NULL,
                tipo TEXT NOT NULL,
                data_cadastro TEXT,
                data_solicitacao TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS equipamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT NOT NULL,
                regional TEXT NOT NULL,
                tipo TEXT NOT NULL,
                data_cadastro TEXT,
                data_solicitacao TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_codigo ON equipamentos(codigo)")

    conn.commit()
    conn.close()

# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------
class IntegrityError(Exception):
    pass

def padronizar_tipo(tipo: str) -> str:
    tipo = tipo.strip().title()
    subs = {
        "De":"de", "Da":"da", "Do":"do", "Dos":"dos", "Das":"das",
        "E":"e", "Em":"em", "Com":"com", "Sem":"sem", "Por":"por",
        "Para":"para", "A":"a", "O":"o", "As":"as", "Os":"os",
        "No":"no", "Na":"na", "Nos":"nos", "Nas":"nas",
        "Pelo":"pelo", "Pela":"pela", "Pelos":"pelos", "Pelas":"pelas",
    }
    parts = tipo.split()
    return " ".join([subs.get(p, p) for p in parts])
