import json
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

    def rollback(self):
        self._conn.rollback()

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
                fabricante TEXT,
                modelo TEXT,
                numero_serie TEXT,
                local_instalacao TEXT,
                idbdit TEXT,
                origem TEXT DEFAULT 'oficio',
                status TEXT DEFAULT 'pendente',
                data_cadastro TEXT,
                data_solicitacao TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS envios (
                id SERIAL PRIMARY KEY,
                equipamento_id INTEGER REFERENCES equipamentos(id) ON DELETE CASCADE,
                id_envio TEXT NOT NULL,
                destino TEXT NOT NULL,
                data_envio TEXT,
                observacao TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pendencias (
                id SERIAL PRIMARY KEY,
                equipamento_id INTEGER REFERENCES equipamentos(id) ON DELETE CASCADE,
                motivo TEXT NOT NULL,
                origem TEXT,
                data_pendencia TEXT,
                resolvida INTEGER DEFAULT 0,
                data_resolucao TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS historico (
                id SERIAL PRIMARY KEY,
                equipamento_id INTEGER REFERENCES equipamentos(id) ON DELETE CASCADE,
                tipo TEXT NOT NULL,
                descricao TEXT,
                data_ocorrencia TEXT,
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
                fabricante TEXT,
                modelo TEXT,
                numero_serie TEXT,
                local_instalacao TEXT,
                idbdit TEXT,
                origem TEXT DEFAULT 'oficio',
                status TEXT DEFAULT 'pendente',
                data_cadastro TEXT,
                data_solicitacao TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_codigo ON equipamentos(codigo)")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS envios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipamento_id INTEGER REFERENCES equipamentos(id) ON DELETE CASCADE,
                id_envio TEXT NOT NULL,
                destino TEXT NOT NULL,
                data_envio TEXT,
                observacao TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pendencias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipamento_id INTEGER REFERENCES equipamentos(id) ON DELETE CASCADE,
                motivo TEXT NOT NULL,
                origem TEXT,
                data_pendencia TEXT,
                resolvida INTEGER DEFAULT 0,
                data_resolucao TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS historico (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipamento_id INTEGER REFERENCES equipamentos(id) ON DELETE CASCADE,
                tipo TEXT NOT NULL,
                descricao TEXT,
                data_ocorrencia TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    conn.commit()
    conn.close()

def _migrate_equipamentos():
    conn = get_db()
    colunas = [
        ("fabricante", "TEXT"),
        ("modelo", "TEXT"),
        ("numero_serie", "TEXT"),
        ("local_instalacao", "TEXT"),
        ("idbdit", "TEXT"),
        ("origem", "TEXT DEFAULT 'oficio'"),
        ("status", "TEXT DEFAULT 'pendente'"),
    ]
    for nome, tipo in colunas:
        try:
            if USING_PG:
                conn.execute(f"ALTER TABLE equipamentos ADD COLUMN IF NOT EXISTS {nome} {tipo}")
            else:
                conn.execute(f"ALTER TABLE equipamentos ADD COLUMN {nome} {tipo}")
            conn.commit()
        except Exception:
            conn.rollback()
            pass
    conn.close()

# roda migração no import
_migrate_equipamentos()

# -----------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------
class IntegrityError(Exception):
    pass

def add_historico(conn, equipamento_id, tipo, descricao, data_ocorrencia=None):
    from datetime import date
    conn.execute(
        "INSERT INTO historico (equipamento_id, tipo, descricao, data_ocorrencia) VALUES (%s, %s, %s, %s)",
        (equipamento_id, tipo, descricao, data_ocorrencia or date.today().isoformat())
    )

def add_envio(conn, equipamento_id, id_envio, destino, data_envio=None, observacao=None):
    conn.execute(
        "INSERT INTO envios (equipamento_id, id_envio, destino, data_envio, observacao) VALUES (%s, %s, %s, %s, %s)",
        (equipamento_id, id_envio, destino, data_envio, observacao)
    )
    add_historico(conn, equipamento_id, 'envio',
        f"Enviado para {destino} | ID: {id_envio}", data_envio)

def add_pendencia(conn, equipamento_id, motivo, origem=None, data_pendencia=None):
    conn.execute(
        "INSERT INTO pendencias (equipamento_id, motivo, origem, data_pendencia) VALUES (%s, %s, %s, %s)",
        (equipamento_id, motivo, origem, data_pendencia)
    )
    add_historico(conn, equipamento_id, 'pendencia',
        f"Pendente: {motivo}", data_pendencia)

def resolve_pendencia(conn, pendencia_id, data_resolucao=None):
    from datetime import date
    conn.execute(
        "UPDATE pendencias SET resolvida = 1, data_resolucao = %s WHERE id = %s",
        (data_resolucao or date.today().isoformat(), pendencia_id)
    )
    cur = conn.execute("SELECT equipamento_id FROM pendencias WHERE id = %s", (pendencia_id,))
    row = cur.fetchone()
    if row:
        add_historico(conn, row['equipamento_id'], 'resolucao',
            'Pendência resolvida', data_resolucao)

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
