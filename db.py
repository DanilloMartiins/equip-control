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
                data_entrada_operacao TEXT,
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
                data_entrada_operacao TEXT,
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

    _migrate_equipamentos(conn)
    conn.commit()
    conn.close()

def _migrate_equipamentos(conn):
    colunas = [
        ("fabricante", "TEXT"),
        ("modelo", "TEXT"),
        ("numero_serie", "TEXT"),
        ("local_instalacao", "TEXT"),
        ("idbdit", "TEXT"),
        ("origem", "TEXT DEFAULT 'oficio'"),
        ("status", "TEXT DEFAULT 'pendente'"),
        ("data_entrada_operacao", "TEXT"),
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

    _normalizar_regionais(conn)
    _migrar_data_cadastro(conn)


def _normalizar_regionais(conn):
    mapeamento = {
        'AXIA NORDESTE': 'AXIA Nordeste',
        'AXIA Nordeste': 'AXIA Nordeste',
        'NORDESTE': 'AXIA Nordeste',
        'Nordeste': 'AXIA Nordeste',
        'nordeste': 'AXIA Nordeste',
        'AXIA SUDESTE': 'AXIA Sudeste',
        'AXIA Sudeste': 'AXIA Sudeste',
        'SUDESTE': 'AXIA Sudeste',
        'Sudeste': 'AXIA Sudeste',
        'sudeste': 'AXIA Sudeste',
        'AXIA SUL': 'AXIA Sul',
        'AXIA Sul': 'AXIA Sul',
        'SUL': 'AXIA Sul',
        'Sul': 'AXIA Sul',
        'sul': 'AXIA Sul',
        'AXIA NORTE': 'AXIA Norte',
        'AXIA Norte': 'AXIA Norte',
        'NORTE': 'AXIA Norte',
        'Norte': 'AXIA Norte',
        'norte': 'AXIA Norte',
    }

    try:
        rows = conn.execute("SELECT DISTINCT regional FROM equipamentos").fetchall()
    except Exception:
        return

    for row in rows:
        regional = row['regional'] if isinstance(row, dict) else row[0]
        if not regional:
            continue

        limpa = regional.split('|', 1)[-1].strip() if '|' in regional else regional.strip()

        if limpa in mapeamento:
            destino = mapeamento[limpa]
        else:
            limpa_lower = limpa.lower()
            destino = None
            for chave, val in mapeamento.items():
                if chave.lower() == limpa_lower:
                    destino = val
                    break
            if not destino:
                continue

        if regional != destino:
            try:
                conn.execute(
                    "UPDATE equipamentos SET regional = %s WHERE regional = %s",
                    (destino, regional)
                )
                conn.commit()
            except Exception:
                conn.rollback()


def _migrar_data_cadastro(conn):
    try:
        colunas = [row[1] if isinstance(row, tuple) else row['column_name']
                   for row in conn.execute(
                       "SELECT column_name FROM information_schema.columns "
                       "WHERE table_name = 'equipamentos'"
                   ).fetchall()]
    except Exception:
        try:
            pragma = conn.execute("PRAGMA table_info(equipamentos)").fetchall()
            colunas = [row[1] if isinstance(row, tuple) else row['name'] for row in pragma]
        except Exception:
            return

    if 'data_entrada_operacao' not in colunas:
        return

    try:
        tem_dados = conn.execute(
            "SELECT COUNT(*) AS total FROM equipamentos "
            "WHERE data_cadastro IS NOT NULL AND data_cadastro != ''"
        ).fetchone()
        total = tem_dados['total'] if isinstance(tem_dados, dict) else tem_dados[0]
        if total and total > 0:
            conn.execute(
                "UPDATE equipamentos SET data_entrada_operacao = data_cadastro, data_cadastro = NULL "
                "WHERE data_entrada_operacao IS NULL OR data_entrada_operacao = ''"
            )
            conn.commit()
    except Exception:
        conn.rollback()

    try:
        conn.execute(
            "UPDATE equipamentos SET regional = %s WHERE regional IS NULL OR TRIM(regional) = ''",
            ('AXIA Nordeste',)
        )
        conn.commit()
    except Exception:
        conn.rollback()

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
