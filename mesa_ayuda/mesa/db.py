# mesa/db.py — MySQL/MariaDB (reemplaza la versión SQLite)
# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import re
from flask import current_app, g
from werkzeug.security import generate_password_hash
from datetime import datetime

import pymysql
import pymysql.cursors

# ── Adaptador SQL SQLite → MySQL ──────────────────────────────────────────────
_DQUOTE_RE = re.compile(r'"([^"]+)"')

def _adapt_sql(sql: str) -> str:
    sql = sql.replace("?", "%s")
    sql = _DQUOTE_RE.sub(r"`\1`", sql)
    sql = re.sub(r'\blast_insert_rowid\(\)', 'LAST_INSERT_ID()', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bsubstr\b', 'SUBSTR', sql, flags=re.IGNORECASE)
    return sql


# ── Wrapper de cursor ─────────────────────────────────────────────────────────
class _CursorWrapper:
    def __init__(self, cur):
        self._cur = cur

    def execute(self, sql: str, params=None):
        self._cur.execute(_adapt_sql(sql), params or ())
        return self

    def executemany(self, sql: str, seq):
        self._cur.executemany(_adapt_sql(sql), seq)
        return self

    def fetchone(self):
        return self._cur.fetchone()  # dict (DictCursor)

    def fetchall(self):
        return self._cur.fetchall()  # list[dict]

    @property
    def lastrowid(self):
        return self._cur.lastrowid

    @property
    def rowcount(self):
        return self._cur.rowcount

    def __iter__(self):
        return iter(self._cur.fetchall())


# ── Wrapper de conexión ───────────────────────────────────────────────────────
class _ConnWrapper:
    def __init__(self, conn):
        self._conn = conn
        self._shared_cur = _CursorWrapper(conn.cursor())

    def execute(self, sql: str, params=None):
        return self._shared_cur.execute(sql, params)

    def executescript(self, script: str):
        """Compatibilidad con sqlite3.executescript — ejecuta cada sentencia."""
        for stmt in script.split(";"):
            stmt = stmt.strip()
            if stmt:
                try:
                    self._shared_cur.execute(stmt)
                except Exception:
                    pass

    def cursor(self) -> _CursorWrapper:
        return _CursorWrapper(self._conn.cursor())

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


# ── Configuración de conexión ─────────────────────────────────────────────────
# ✅ Variables alineadas con el .env (MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB)
def _mysql_cfg() -> dict:
    return {
        "host":        os.environ.get("MYSQL_HOST",     "127.0.0.1"),
        "port":        int(os.environ.get("MYSQL_PORT", "3306")),
        "user":        os.environ.get("MYSQL_USER",     "root"),
        "password":    os.environ.get("MYSQL_PASSWORD", ""),
        "database":    os.environ.get("MYSQL_DB",       "mesa_ayuda"),
        "charset":     "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit":  False,
    }


# ── get_db / close_db (mismo API que la versión SQLite) ──────────────────────
def get_db() -> _ConnWrapper:
    if 'db' not in g:
        raw = pymysql.connect(**_mysql_cfg())
        g.db = _ConnWrapper(raw)
    return g.db

def close_db(_=None):
    db = g.pop('db', None)
    if db is not None:
        try:
            db._conn.commit()
        except Exception:
            pass
        db.close()


# ── Schemas ───────────────────────────────────────────────────────────────────
SCHEMA_USERS = """
CREATE TABLE IF NOT EXISTS users (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  username      VARCHAR(150) UNIQUE NOT NULL,
  display_name  VARCHAR(255) NOT NULL,
  password_hash VARCHAR(512) NOT NULL,
  role          ENUM('admin','usuario') NOT NULL,
  created_at    VARCHAR(30)  NOT NULL,
  firma_img     LONGTEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

SCHEMA_TICKETS = """
CREATE TABLE IF NOT EXISTS tickets (
    id                              INT AUTO_INCREMENT PRIMARY KEY,
    created_by                      INT  NOT NULL,
    created_at                      VARCHAR(50)  NOT NULL,
    numero_ticket                   VARCHAR(50),
    fecha_inicio                    VARCHAR(20),
    fecha_final                     VARCHAR(20),
    hora_inicio                     VARCHAR(10),
    hora_final                      VARCHAR(10),
    sede                            VARCHAR(100),
    ubicacion                       VARCHAR(255),
    soporte_hardware                TINYINT(1) DEFAULT 0,
    soporte_Software                TINYINT(1) DEFAULT 0,
    soporte_redes                   TINYINT(1) DEFAULT 0,
    equipo_equipo                   VARCHAR(100),
    equipo_marca                    VARCHAR(100),
    equipo_modelo                   VARCHAR(100),
    equipo_cod_inventario           VARCHAR(100),
    equipo_coin                     VARCHAR(100),
    equipo_disco                    VARCHAR(50),
    equipo_ram                      VARCHAR(50),
    equipo_procesador               VARCHAR(100),
    servicio_tipo                   VARCHAR(100),
    servicio_otro                   VARCHAR(255),
    falla_asociada                  VARCHAR(255),
    descripcion_solicitud           TEXT,
    descripcion_trabajo             TEXT,
    eval_calidad_servicio           INT,
    eval_calidad_informacion        INT,
    eval_oportunidad_respuesta      INT,
    eval_actitud_tecnico            INT,
    firma_usuario_gestiona_img      LONGTEXT,
    firma_tecnico_mantenimiento_img LONGTEXT,
    firma_logistica_img             LONGTEXT,
    firma_supervisor_img            LONGTEXT,
    firma_usuario_gestiona_nombre   VARCHAR(255),
    firma_tecnico_mantenimiento_nombre VARCHAR(255),
    firma_logistica_nombre          VARCHAR(255),
    firma_supervisor_nombre         VARCHAR(255),
    estado                          VARCHAR(30) DEFAULT 'abierto',
    finalizado_at                   VARCHAR(50),
    FOREIGN KEY(created_by) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""


# ── init_db ───────────────────────────────────────────────────────────────────
def init_db():
    db = get_db()
    cur = db.cursor()

    for ddl in [SCHEMA_USERS, SCHEMA_TICKETS]:
        cur.execute(ddl)

    cur.execute("SHOW COLUMNS FROM tickets LIKE %s", ('numero_ticket',))
    if not cur.fetchone():
        cur.execute("ALTER TABLE tickets ADD COLUMN numero_ticket VARCHAR(50) AFTER created_at")

    db.commit()

    # Crear admin por defecto si no hay usuarios
    row = db.execute("SELECT COUNT(*) AS c FROM users").fetchone()
    if (row or {}).get('c', 0) == 0:
        db.execute(
            "INSERT INTO users (username, display_name, password_hash, role, created_at) VALUES (%s,%s,%s,%s,%s)",
            ('admin', 'Administrador', generate_password_hash('admin123'), 'admin',
             datetime.utcnow().isoformat())
        )
        db.commit()