"""Persistência SQLite. Fotos originais não são gravadas."""
import json
import sqlite3
import time
from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL, login TEXT NOT NULL UNIQUE,
 password_hash TEXT,
 level INTEGER NOT NULL CHECK(level IN (1,2,3)),
 active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS one_minister ON users(level) WHERE level=3;
CREATE TABLE IF NOT EXISTS samples (
 id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 vector TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS records (
 id INTEGER PRIMARY KEY, title TEXT NOT NULL, region TEXT NOT NULL,
 level INTEGER NOT NULL CHECK(level IN (1,2,3)), body TEXT NOT NULL,
 updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
 token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 expires_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS audit (
 id INTEGER PRIMARY KEY, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
 user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
 event TEXT NOT NULL, detail TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS attempts (address TEXT NOT NULL, stamp REAL NOT NULL);
CREATE INDEX IF NOT EXISTS attempts_lookup ON attempts(address, stamp);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS face_challenges (
 token_hash TEXT PRIMARY KEY,
 user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 expires_at REAL NOT NULL, attempts INTEGER NOT NULL DEFAULT 0
);
"""

SEED = [
 ("Panorama de monitoramento hídrico", "Nacional", 1,
  "Boletim demonstrativo: campanhas de coleta acompanham a qualidade da água em bacias rurais. As localidades, valores e ocorrências deste sistema são fictícios.", "2026-09-01"),
 ("Como comunicar uma ocorrência ambiental", "Nacional", 1,
  "Material educativo fictício: registre a localização e a descrição da ocorrência. Não entre em propriedades privadas para realizar a coleta de evidências.", "2026-09-02"),
 ("Programa de acompanhamento de nascentes", "Bacia Aurora (fictícia)", 1,
  "Cenário didático com 12 pontos de observação e visitas mensais. Este registro não representa uma operação real do Ministério do Meio Ambiente.", "2026-09-03"),
 ("Investigação • Fazenda Horizonte", "Divisão Sudeste (fictícia)", 2,
  "Dossiê fictício: propriedade PR-014; amostras A-102 e A-103; indícios simulados do composto proibido fictício AGX-7 em drenagem. Encaminhamento: nova coleta e análise técnica. Nenhuma acusação real.", "2026-09-04"),
 ("Investigação • Sítio Vale Claro", "Divisão Sul (fictícia)", 2,
  "Dossiê fictício: propriedade PR-027; amostra B-204; cenário simulado de possível transporte de resíduos até um afluente. Pendência: conferir o laudo e o histórico de manejo.", "2026-09-05"),
 ("Diretriz de resposta inter-regional", "Gabinete (fictício)", 3,
  "Documento estratégico fictício, reservado ao ministro: priorizar a integração entre divisões e o acompanhamento das bacias Aurora e Cedro. Proposta simulada de distribuição de recursos; não representa decisão governamental.", "2026-09-06"),
]


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"], timeout=30)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db


def init_db():
    db = get_db()
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript(SCHEMA)
    # Migração aditiva: conserva usuários, vetores, documentos e histórico da v1.
    columns = {row["name"] for row in db.execute("PRAGMA table_info(users)")}
    if "password_hash" not in columns:
        db.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
    if db.execute("PRAGMA user_version").fetchone()[0] < 2:
        db.execute("DELETE FROM sessions")  # Sessões antigas não comprovam a senha.
        db.execute("PRAGMA user_version=2")
    if not db.execute("SELECT 1 FROM records LIMIT 1").fetchone():
        db.executemany("INSERT INTO records(title,region,level,body,updated_at) VALUES(?,?,?,?,?)", SEED)
    db.commit()


def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def candidates():
    db = get_db()
    users = {r["id"]: dict(r) | {"vectors": []} for r in db.execute("SELECT id,name,login,level FROM users WHERE active=1")}
    for row in db.execute("SELECT user_id, vector FROM samples"):
        if row["user_id"] in users:
            users[row["user_id"]]["vectors"].append(json.loads(row["vector"]))
    return [u for u in users.values() if u["vectors"]]


def audit(event, detail, user_id=None):
    db = get_db()
    db.execute("INSERT INTO audit(user_id,event,detail) VALUES(?,?,?)", (user_id, event, detail))
    db.execute("DELETE FROM sessions WHERE expires_at < ?", (time.time(),))
    db.commit()
