"""Senha e rosto são obrigatórios; a etapa intermediária não autoriza acesso."""
from functools import wraps
from hashlib import sha256
import secrets
import time

from flask import abort, current_app, g, jsonify, redirect, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from .db import audit, candidates, get_db
from .face import rank_candidates

USER_FIELDS = "u.id,u.name,u.login,u.level,u.active,u.created_at"


def digest(value):
    return sha256(value.encode()).hexdigest()


def password_from_form():
    password = request.form.get("password", "")
    if not 8 <= len(password) <= 128:
        abort(400, "Use uma senha de 8 a 128 caracteres.")
    if password != request.form.get("password_confirm", ""):
        abort(400, "As senhas não coincidem. Confira a confirmação.")
    return generate_password_hash(password, method="scrypt")


def current_user():
    if "user" not in g:
        token = session.get("auth_token", "")
        row = get_db().execute(
            f"SELECT {USER_FIELDS} FROM sessions s JOIN users u ON u.id=s.user_id "
            "WHERE s.token_hash=? AND s.expires_at>? AND u.active=1 AND u.password_hash IS NOT NULL",
            (digest(token), time.time()),
        ).fetchone() if token else None
        g.user = dict(row) if row else None
    return g.user


def require_level(level):
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            user = current_user()
            if not user:
                if request.path.startswith("/api/"):
                    abort(401, "Entre com usuário, senha e confirmação facial para continuar.")
                return redirect("/entrar")
            if user["level"] < level:
                abort(403, "Seu perfil não tem acesso a esta área.")
            return fn(*args, **kwargs)
        return wrapped
    return decorator


def clear_identity():
    db = get_db()
    for field, table in (("auth_token", "sessions"), ("face_token", "face_challenges")):
        token = session.pop(field, None)
        if token:
            db.execute(f"DELETE FROM {table} WHERE token_hash=?", (digest(token),))
    db.commit()
    g.user = None


def pending_identity():
    token = session.get("face_token", "")
    if not token:
        return None
    row = get_db().execute(
        "SELECT c.token_hash,c.expires_at,c.attempts,u.id,u.name,u.login "
        "FROM face_challenges c JOIN users u ON u.id=c.user_id "
        "WHERE c.token_hash=? AND c.expires_at>? AND c.attempts<5 AND u.active=1 "
        "AND u.password_hash IS NOT NULL", (digest(token), time.time()),
    ).fetchone()
    return dict(row) if row else None


def matched_identity(probe, expected_id):
    ranked = rank_candidates(probe, candidates())
    if not ranked or ranked[0][0] < current_app.config["FACE_THRESHOLD"]:
        return None
    if ranked[0][1]["id"] != expected_id:
        return None
    if len(ranked) > 1 and ranked[0][0] - ranked[1][0] < current_app.config["FACE_MARGIN"]:
        return None
    return ranked[0]


def needs_password_setup():
    return bool(get_db().execute("SELECT 1 FROM users WHERE password_hash IS NULL AND active=1 LIMIT 1").fetchone())


def register_auth(app, extract_uploads):
    # Mesmo custo de verificação para nomes inexistentes; hash nunca sai do servidor.
    dummy_hash = generate_password_hash(secrets.token_urlsafe(24), method="scrypt")

    @app.post("/api/auth/password")
    def password_step():
        clear_identity()
        name = request.form.get("login", "").strip().lower()
        password = request.form.get("password", "")
        row = get_db().execute("SELECT id,login,password_hash,active FROM users WHERE login=?", (name,)).fetchone()
        if not 1 <= len(password) <= 128 or len(name) > 40:
            abort(401, "Usuário ou senha inválidos. Confira os dados e tente novamente.")
        valid = check_password_hash(row["password_hash"] if row and row["password_hash"] else dummy_hash, password)
        if not row or not row["active"] or not valid or not row["password_hash"]:
            audit("senha_negada", "Credenciais não confirmadas")
            abort(401, "Usuário ou senha inválidos. Confira os dados e tente novamente.")
        session.clear()
        session["csrf"] = secrets.token_urlsafe(32)
        session["face_token"] = secrets.token_urlsafe(32)
        db = get_db()
        db.execute("BEGIN IMMEDIATE")
        fresh = db.execute("SELECT password_hash,active FROM users WHERE id=?", (row["id"],)).fetchone()
        if not fresh or not fresh["active"] or fresh["password_hash"] != row["password_hash"]:
            db.rollback()
            session.clear()
            abort(401, "O cadastro foi atualizado. Informe usuário e senha novamente.")
        db.execute("DELETE FROM face_challenges WHERE expires_at<?", (time.time(),))
        db.execute("INSERT INTO face_challenges(token_hash,user_id,expires_at) VALUES(?,?,?)",
                   (digest(session["face_token"]), row["id"], time.time()+300))
        db.commit()
        return jsonify(next="/confirmar-rosto")

    @app.post("/api/auth/cancel")
    def cancel_login():
        clear_identity()
        session.clear()
        return jsonify(next="/entrar")

    @app.post("/api/login")
    def face_step():
        pending = pending_identity()
        if not pending:
            abort(401, "Etapa expirada. Volte ao login e informe usuário e senha novamente.")
        # Reserva uma tentativa antes da inferência; arquivos inválidos também contam.
        db = get_db()
        changed = db.execute("UPDATE face_challenges SET attempts=attempts+1 "
                             "WHERE token_hash=? AND attempts<5 AND expires_at>?",
                             (pending["token_hash"], time.time())).rowcount
        db.commit()
        if not changed:
            abort(401, "Etapa expirada. Volte ao login.")
        match = matched_identity(extract_uploads(1)[0], pending["id"])
        if not match:
            audit("autenticacao_negada", "Rosto não corresponde ao usuário ou resultado ambíguo", pending["id"])
            abort(401, "O rosto não foi confirmado para este usuário. Tente outra foto ou troque de usuário.")
        # Revalida e consome o desafio uma única vez, inclusive sob concorrência.
        db.execute("BEGIN IMMEDIATE")
        fresh = db.execute("SELECT c.user_id FROM face_challenges c JOIN users u ON u.id=c.user_id "
                           "WHERE c.token_hash=? AND c.expires_at>? AND u.active=1 AND u.password_hash IS NOT NULL",
                           (pending["token_hash"], time.time())).fetchone()
        if not fresh:
            db.rollback()
            abort(401, "A etapa expirou ou foi cancelada. Entre novamente.")
        db.execute("DELETE FROM face_challenges WHERE token_hash=?", (pending["token_hash"],))
        auth_token = secrets.token_urlsafe(32)
        db.execute("INSERT INTO sessions VALUES(?,?,?)",
                   (digest(auth_token), pending["id"], time.time()+app.config["SESSION_SECONDS"]))
        audit("autenticacao_aceita", f"Senha e rosto; similaridade {match[0]:.3f}", pending["id"])
        session.clear()
        session["csrf"] = secrets.token_urlsafe(32)
        session["auth_token"] = auth_token
        session.permanent = True
        return jsonify(message="Acesso confirmado.", next="/painel")

    @app.post("/api/activate")
    def activate_legacy_account():
        if not needs_password_setup():
            abort(409, "Todos os cadastros já possuem senha.")
        name = request.form.get("login", "").strip().lower()
        code = request.form.get("activation_code", "")
        db = get_db()
        expected = db.execute("SELECT value FROM settings WHERE key='activation_hash'").fetchone()
        row = db.execute("SELECT id FROM users WHERE login=? AND password_hash IS NULL AND active=1", (name,)).fetchone()
        if not expected or not secrets.compare_digest(digest(code), expected[0]) or not row:
            abort(403, "Não foi possível ativar. Confira o usuário e o código exibido no terminal.")
        password_hash = password_from_form()
        if not matched_identity(extract_uploads(1)[0], row["id"]):
            audit("ativacao_negada", "Rosto não confirmado para o cadastro", row["id"])
            abort(401, "O rosto não corresponde a este cadastro. A senha não foi alterada.")
        db.execute("BEGIN IMMEDIATE")
        fresh_code = db.execute("SELECT value FROM settings WHERE key='activation_hash'").fetchone()
        if not fresh_code or not secrets.compare_digest(digest(code), fresh_code[0]):
            db.rollback()
            abort(403, "Código de ativação expirado. Confira o terminal.")
        changed = db.execute("UPDATE users SET password_hash=? WHERE id=? AND password_hash IS NULL AND active=1",
                             (password_hash, row["id"])).rowcount
        if not changed:
            db.rollback()
            abort(409, "Este cadastro já foi atualizado ou desativado.")
        db.execute("DELETE FROM sessions WHERE user_id=?", (row["id"],))
        db.execute("DELETE FROM face_challenges WHERE user_id=?", (row["id"],))
        if not needs_password_setup():
            db.execute("DELETE FROM settings WHERE key='activation_hash'")
        audit("senha_definida", "Cadastro anterior atualizado com confirmação facial", row["id"])
        clear_identity()
        return jsonify(message="Senha criada. Entre com seu usuário e senha.", next="/entrar?ativada=1")

    @app.post("/api/logout")
    def logout():
        user = current_user()
        clear_identity()
        audit("saida", "Sessão encerrada", user["id"] if user else None)
        session.clear()
        return jsonify(next="/entrar")


def issue_activation_code(app):
    with app.app_context():
        if not needs_password_setup():
            return None
        token = secrets.token_urlsafe(18)
        db = get_db()
        db.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('activation_hash',?)", (digest(token),))
        db.commit()
        return token
